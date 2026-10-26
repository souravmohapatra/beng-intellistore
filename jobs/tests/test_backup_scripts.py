"""Behavioral tests for the containerized backup and restore scripts."""

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time
from django.test import SimpleTestCase

BASE_DIR = Path(__file__).resolve().parents[2]
BACKUP = BASE_DIR / "scripts" / "backup_generation.sh"
RESTORE = BASE_DIR / "scripts" / "restore_generation.sh"


class ScriptTestCase(SimpleTestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.root, ignore_errors=True))
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.backup_dir = self.root / "backup"
        self.originals = self.root / "data" / "originals"
        self.originals.mkdir(parents=True)
        self.log = self.root / "calls.log"
        self.fail_dump = False

    def fake(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
        return path

    def install_fakes(self):
        dump_body = "cat <<'EOF'\nFAKE-CUSTOM-DUMP\nEOF\n"
        if self.fail_dump:
            dump_body = "echo 'dump failed' >&2\nexit 1\n"
        self.fake("pg_dump", f'echo "pg_dump $*" >> "{self.log}"\n{dump_body}')
        self.fake("psql", f'echo "psql $*" >> "{self.log}"\n')
        self.fake(
            "pg_restore",
            f'echo "pg_restore $*" >> "{self.log}"\ncat > /dev/null\n',
        )

    def env(self, **overrides):
        env = {
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "BACKUP_DIR": str(self.backup_dir),
            "STATUS_FILE": str(self.root / "status" / "backup.json"),
            "SUCCESS_FILE": str(self.root / "status" / "backup-last-success.json"),
            "ORIGINALS_DIR": str(self.originals),
            "PGHOST": "fake-host",
            "PGUSER": "fake-user",
            "PGDATABASE": "intellistore",
            "KEEP_GENERATIONS": "7",
        }
        env.update(overrides)
        return env

    def invoke(self, script, args=(), **env):
        return subprocess.run(
            ["sh", str(script), *args],
            env=self.env(**env),
            capture_output=True,
            text=True,
            timeout=30,
        )

    def original(self, name, content):
        path = self.originals / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path


class BackupGenerationTests(ScriptTestCase):
    def test_success_writes_complete_generation_with_manifest(self):
        self.install_fakes()
        self.original("ab/abcd", b"original-bytes")

        result = self.invoke(BACKUP)

        self.assertEqual(result.returncode, 0, result.stderr)
        generations = list(self.backup_dir.glob("generation-*"))
        self.assertEqual(len(generations), 1)
        generation = generations[0]
        self.assertTrue((generation / "COMPLETE").exists())
        self.assertEqual((generation / "database.dump").read_bytes(), b"FAKE-CUSTOM-DUMP\n")
        self.assertEqual(
            (generation / "originals" / "ab" / "abcd").read_bytes(), b"original-bytes"
        )
        manifest = (generation / "MANIFEST.sha256").read_text().splitlines()
        self.assertEqual(len(manifest), 2)
        expected = hashlib.sha256(b"original-bytes").hexdigest()
        self.assertTrue(any(expected in line and "originals/ab/abcd" in line for line in manifest))
        self.assertIn("pg_dump", self.log.read_text())
        status = (self.root / "status" / "backup.json").read_text()
        self.assertIn('"status":"success"', status)
        self.assertIn(str(generation), status)

    def test_failed_dump_is_not_counted_and_keeps_an_incomplete_marker(self):
        self.fail_dump = True
        self.install_fakes()

        result = self.invoke(BACKUP)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.backup_dir.glob("generation-*")), [])
        incomplete = list(self.backup_dir.glob(".incomplete-*"))
        self.assertEqual(len(incomplete), 1)
        self.assertTrue((incomplete[0] / "FAILED").exists())
        status = (self.root / "status" / "backup.json").read_text()
        self.assertIn('"status":"failed"', status)

    def test_missing_originals_parent_fails_without_publishing(self):
        self.install_fakes()
        missing = self.root / "missing-parent" / "originals"

        result = self.invoke(BACKUP, ORIGINALS_DIR=str(missing))

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.backup_dir.glob("generation-*")), [])
        status = (self.root / "status" / "backup.json").read_text()
        self.assertIn('"status":"failed"', status)

    def test_unreadable_original_payload_fails_without_publishing(self):
        self.install_fakes()
        path = self.original("ab/abcd", b"secret")
        path.chmod(0)

        result = self.invoke(BACKUP)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.backup_dir.glob("generation-*")), [])

    def test_failure_preserves_the_previous_success_record(self):
        self.install_fakes()
        first = self.invoke(BACKUP)
        self.assertEqual(first.returncode, 0, first.stderr)
        success_before = (self.root / "status" / "backup-last-success.json").read_text()

        self.fail_dump = True
        self.install_fakes()
        second = self.invoke(BACKUP)

        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(
            (self.root / "status" / "backup-last-success.json").read_text(),
            success_before,
        )
        status = (self.root / "status" / "backup.json").read_text()
        self.assertIn('"status":"failed"', status)

    def test_retention_keeps_seven_newest_complete_generations(self):
        self.install_fakes()
        for index in range(8):
            old = self.backup_dir / f"generation-2020010{index}T000000Z"
            old.mkdir(parents=True)
            (old / "COMPLETE").write_text("created_at=old\n")

        result = self.invoke(BACKUP)

        self.assertEqual(result.returncode, 0, result.stderr)
        remaining = sorted(path.name for path in self.backup_dir.glob("generation-*"))
        self.assertEqual(len(remaining), 7)
        self.assertNotIn("generation-20200100T000000Z", remaining)

    def test_failure_never_retires_a_good_generation(self):
        self.fail_dump = True
        self.install_fakes()
        for index in range(8):
            old = self.backup_dir / f"generation-2020010{index}T000000Z"
            old.mkdir(parents=True)
            (old / "COMPLETE").write_text("created_at=old\n")

        result = self.invoke(BACKUP)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(list(self.backup_dir.glob("generation-*"))), 8)

    def test_empty_originals_directory_still_publishes(self):
        self.install_fakes()

        result = self.invoke(BACKUP)

        self.assertEqual(result.returncode, 0, result.stderr)
        generations = list(self.backup_dir.glob("generation-*"))
        self.assertEqual(len(generations), 1)
        self.assertTrue((generations[0] / "originals").is_dir())
        manifest = (generations[0] / "MANIFEST.sha256").read_text().splitlines()
        self.assertEqual(len(manifest), 1)
        self.assertIn("database.dump", manifest[0])

    def test_rejects_a_symlinked_original_without_publishing(self):
        self.install_fakes()
        target = self.original("ab/real", b"original-bytes")
        os.symlink(target, self.originals / "ab" / "link")

        result = self.invoke(BACKUP)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr)
        self.assertEqual(list(self.backup_dir.glob("generation-*")), [])
        status = (self.root / "status" / "backup.json").read_text()
        self.assertIn('"status":"failed"', status)

    def test_fails_closed_when_payload_enumeration_fails(self):
        self.install_fakes()
        self.fake("find", "echo 'find: boom' >&2\nexit 1\n")

        result = self.invoke(BACKUP)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.backup_dir.glob("generation-*")), [])
        status = (self.root / "status" / "backup.json").read_text()
        self.assertIn('"status":"failed"', status)

    def test_fails_closed_when_payload_hashing_fails(self):
        self.install_fakes()
        self.fake("sha256sum", "echo 'sha256sum: boom' >&2\nexit 1\n")

        result = self.invoke(BACKUP)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.backup_dir.glob("generation-*")), [])
        status = (self.root / "status" / "backup.json").read_text()
        self.assertIn('"status":"failed"', status)

    def test_second_backup_in_the_same_second_is_retained(self):
        self.install_fakes()
        self.original("ab/abcd", b"original-bytes")
        # Freeze the clock so both runs share one timestamp.
        self.fake("date", "echo 20260101T030000Z\n")

        first = self.invoke(BACKUP, KEEP_GENERATIONS="1")
        self.assertEqual(first.returncode, 0, first.stderr)
        first_generations = sorted(self.backup_dir.glob("generation-*"))
        self.assertEqual(len(first_generations), 1)

        second = self.invoke(BACKUP, KEEP_GENERATIONS="1")
        self.assertEqual(second.returncode, 0, second.stderr)

        generations = sorted(self.backup_dir.glob("generation-*"))
        self.assertEqual(len(generations), 1)
        self.assertNotEqual(generations[0], first_generations[0])
        status = json.loads((self.root / "status" / "backup.json").read_text())
        self.assertEqual(status["generation"], str(generations[0]))
        self.assertTrue((generations[0] / "COMPLETE").exists())

    def test_retention_uses_publication_order_not_names(self):
        self.install_fakes()
        self.original("ab/abcd", b"original-bytes")
        self.fake("date", "echo 20260101T030000Z\n")
        # Same frozen second: the newer generation has the lexicographically
        # lower suffix, so name ordering would wrongly keep the older one.
        older = self.backup_dir / "generation-20260101T030000Z-zzzzzz"
        older.mkdir(parents=True)
        (older / "COMPLETE").write_text("created_at=old\nseq=5\n")
        newer = self.backup_dir / "generation-20260101T030000Z-aaaaaa"
        newer.mkdir(parents=True)
        (newer / "COMPLETE").write_text("created_at=old\nseq=6\n")

        result = self.invoke(BACKUP, KEEP_GENERATIONS="1")

        self.assertEqual(result.returncode, 0, result.stderr)
        generations = sorted(self.backup_dir.glob("generation-*"))
        self.assertEqual(len(generations), 1)
        self.assertNotIn(generations[0].name, {older.name, newer.name})
        status = json.loads((self.root / "status" / "backup.json").read_text())
        self.assertEqual(status["generation"], str(generations[0]))
        self.assertTrue((generations[0] / "COMPLETE").exists())

    def test_destination_lock_creation_failure_records_failed_attempt(self):
        self.install_fakes()
        self.original("ab/abcd", b"original-bytes")
        first = self.invoke(BACKUP)
        self.assertEqual(first.returncode, 0, first.stderr)
        success_file = self.root / "status" / "backup-last-success.json"
        previous_success = success_file.read_bytes()
        generation = Path(json.loads(previous_success)["generation"])
        self.fake(
            "mkdir",
            'if [ "$1" = "$BACKUP_DIR/.backup.lock" ]; then exit 1; fi\n'
            'exec /bin/mkdir "$@"\n',
        )

        failed = self.invoke(BACKUP)

        self.assertNotEqual(failed.returncode, 0)
        attempt = json.loads((self.root / "status" / "backup.json").read_text())
        self.assertEqual(attempt["status"], "failed")
        self.assertEqual(success_file.read_bytes(), previous_success)
        self.assertTrue((generation / "COMPLETE").exists())

    def test_refuses_when_another_backup_holds_the_lock(self):
        self.install_fakes()
        lock = self.backup_dir / ".backup.lock"
        lock.mkdir(parents=True)
        (lock / "owner").write_text("1\n")

        result = self.invoke(BACKUP)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("another backup", result.stderr)
        self.assertEqual(list(self.backup_dir.glob("generation-*")), [])
        self.assertFalse((self.root / "status" / "backup.json").exists())
        self.assertTrue(lock.exists())

    def test_refuses_an_old_lock_regardless_of_age(self):
        self.install_fakes()
        self.original("ab/abcd", b"original-bytes")
        good = self.backup_dir / "generation-20260101T030000Z-aaaaaaaa"
        good.mkdir(parents=True)
        (good / "COMPLETE").write_text("created_at=good\nseq=1\n")
        status_dir = self.root / "status"
        status_dir.mkdir()
        status_before = '{"status":"success","generation":"old"}\n'
        (status_dir / "backup.json").write_text(status_before)
        lock = self.backup_dir / ".backup.lock"
        lock.mkdir()
        stale = time.time() - 7200
        os.utime(lock, (stale, stale))

        result = self.invoke(BACKUP)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("another backup", result.stderr)
        self.assertTrue(lock.exists())
        self.assertEqual(
            sorted(path.name for path in self.backup_dir.glob("generation-*")),
            [good.name],
        )
        self.assertEqual((status_dir / "backup.json").read_text(), status_before)

    def test_status_json_survives_quotes_in_paths(self):
        self.install_fakes()
        self.original("ab/abcd", b"original-bytes")
        quoted = self.root / 'back"up\\dir'

        result = self.invoke(BACKUP, BACKUP_DIR=str(quoted))

        self.assertEqual(result.returncode, 0, result.stderr)
        status = json.loads((self.root / "status" / "backup.json").read_text())
        self.assertEqual(status["status"], "success")
        self.assertTrue(status["generation"].startswith(str(quoted)))


class RestoreGenerationTests(ScriptTestCase):
    def build_generation(self, name="generation-20260101T030000Z"):
        generation = self.backup_dir / name
        (generation / "originals" / "ab").mkdir(parents=True)
        (generation / "originals" / "ab" / "abcd").write_bytes(b"original-bytes")
        (generation / "database.dump").write_bytes(b"FAKE-CUSTOM-DUMP\n")
        lines = []
        for file in sorted(generation.rglob("*")):
            if file.is_file() and file.name != "MANIFEST.sha256":
                content = file.read_bytes()
                lines.append(
                    f"{hashlib.sha256(content).hexdigest()}  {len(content)}  "
                    f"{file.relative_to(generation)}"
                )
        (generation / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
        (generation / "COMPLETE").write_text("created_at=test\n")
        return generation

    def test_restores_verified_originals_into_an_empty_target(self):
        self.install_fakes()
        generation = self.build_generation()
        target = self.root / "restore-target"

        result = self.invoke(
            RESTORE,
            [
                "--generation",
                str(generation),
                "--database",
                "intellistore_restore_check",
                "--originals-target",
                str(target),
            ],
            LIVE_DATABASE="intellistore",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((target / "ab" / "abcd").read_bytes(), b"original-bytes")
        log = self.log.read_text()
        self.assertIn("intellistore_restore_check", log)
        self.assertIn("pg_restore", log)

    def test_rejects_an_empty_manifest_before_any_write(self):
        self.install_fakes()
        generation = self.build_generation()
        (generation / "MANIFEST.sha256").write_text("")

        result = self.invoke(
            RESTORE,
            [
                "--generation",
                str(generation),
                "--database",
                "intellistore_restore_check",
                "--originals-target",
                str(self.root / "restore-target"),
            ],
            LIVE_DATABASE="intellistore",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "restore-target").exists())
        self.assertFalse(self.log.exists())

    def test_rejects_a_manifest_that_omits_an_original(self):
        self.install_fakes()
        generation = self.build_generation()
        lines = [
            line
            for line in (generation / "MANIFEST.sha256").read_text().splitlines()
            if "originals/" not in line
        ]
        (generation / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")

        result = self.invoke(
            RESTORE,
            [
                "--generation",
                str(generation),
                "--database",
                "intellistore_restore_check",
                "--originals-target",
                str(self.root / "restore-target"),
            ],
            LIVE_DATABASE="intellistore",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not cover every original", result.stderr)
        self.assertFalse(self.log.exists())

    def test_rejects_an_unsafe_manifest_path(self):
        self.install_fakes()
        generation = self.build_generation()
        content = b"escape"
        line = (
            f"{hashlib.sha256(content).hexdigest()}  {len(content)}  ../escape\n"
        )
        with (generation / "MANIFEST.sha256").open("a") as manifest:
            manifest.write(line)

        result = self.invoke(
            RESTORE,
            [
                "--generation",
                str(generation),
                "--database",
                "intellistore_restore_check",
                "--originals-target",
                str(self.root / "restore-target"),
            ],
            LIVE_DATABASE="intellistore",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsafe", result.stderr)
        self.assertFalse(self.log.exists())

    def test_refuses_to_restore_over_the_live_database(self):
        self.install_fakes()
        generation = self.build_generation()

        result = self.invoke(
            RESTORE,
            [
                "--generation",
                str(generation),
                "--database",
                "intellistore",
                "--originals-target",
                str(self.root / "restore-target"),
            ],
            LIVE_DATABASE="intellistore",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing", result.stderr)

    def test_rejects_an_incomplete_generation(self):
        self.install_fakes()
        generation = self.build_generation()
        (generation / "COMPLETE").unlink()

        result = self.invoke(
            RESTORE,
            [
                "--generation",
                str(generation),
                "--database",
                "intellistore_restore_check",
                "--originals-target",
                str(self.root / "restore-target"),
            ],
            LIVE_DATABASE="intellistore",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("incomplete", result.stderr)
        self.assertFalse((self.root / "restore-target").exists())

    def test_rejects_corrupted_payload_before_writing(self):
        self.install_fakes()
        generation = self.build_generation()
        (generation / "originals" / "ab" / "abcd").write_bytes(b"tampered")

        result = self.invoke(
            RESTORE,
            [
                "--generation",
                str(generation),
                "--database",
                "intellistore_restore_check",
                "--originals-target",
                str(self.root / "restore-target"),
            ],
            LIVE_DATABASE="intellistore",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manifest mismatch", result.stderr)
        self.assertFalse((self.root / "restore-target").exists())

    def restore(self, generation, database="intellistore_restore_check", target=None):
        return self.invoke(
            RESTORE,
            [
                "--generation",
                str(generation),
                "--database",
                database,
                "--originals-target",
                str(target if target is not None else self.root / "restore-target"),
            ],
            LIVE_DATABASE="intellistore",
        )

    def test_rejects_injected_database_identifier_before_any_write(self):
        self.install_fakes()
        generation = self.build_generation()

        for bad in ('intellistore"; DROP DATABASE intellistore; --', "bad name", 'quote"name'):
            with self.subTest(identifier=bad):
                result = self.restore(generation, database=bad)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("identifier", result.stderr)
                self.assertFalse((self.root / "restore-target").exists())
                self.assertFalse(self.log.exists())

    def test_rejects_an_over_long_database_identifier(self):
        self.install_fakes()
        generation = self.build_generation()

        result = self.restore(generation, database="d" * 64)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("63", result.stderr)
        self.assertFalse(self.log.exists())

    def test_rejects_a_symlinked_dump_before_any_write(self):
        self.install_fakes()
        generation = self.build_generation()
        dump = generation / "database.dump"
        real = generation / "real.dump"
        real.write_bytes(dump.read_bytes())
        dump.unlink()
        os.symlink(real, dump)

        result = self.restore(generation)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symbolic link", result.stderr)
        self.assertFalse(self.log.exists())

    def test_rejects_a_symlinked_manifest_before_any_write(self):
        self.install_fakes()
        generation = self.build_generation()
        manifest = generation / "MANIFEST.sha256"
        real = generation / "real.manifest"
        real.write_text(manifest.read_text())
        manifest.unlink()
        os.symlink(real, manifest)

        result = self.restore(generation)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symbolic link", result.stderr)
        self.assertFalse(self.log.exists())

    def test_rejects_a_symlinked_original_before_any_write(self):
        self.install_fakes()
        generation = self.build_generation()
        original = generation / "originals" / "ab" / "abcd"
        real = generation / "originals" / "ab" / "real"
        real.write_bytes(original.read_bytes())
        original.unlink()
        os.symlink(real, original)

        result = self.restore(generation)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symbolic link", result.stderr)
        self.assertFalse(self.log.exists())

    def test_injected_enumeration_failure_writes_nothing(self):
        self.install_fakes()
        self.fake("find", "exit 1\n")
        generation = self.build_generation()

        result = self.restore(generation)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())
        self.assertFalse((self.root / "restore-target").exists())

    def test_injected_hashing_failure_writes_nothing(self):
        self.install_fakes()
        self.fake("sha256sum", "exit 1\n")
        generation = self.build_generation()

        result = self.restore(generation)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())
        self.assertFalse((self.root / "restore-target").exists())

    def test_restores_a_generation_with_no_originals(self):
        self.install_fakes()
        generation = self.build_generation()
        __import__("shutil").rmtree(generation / "originals")
        dump = (generation / "database.dump").read_bytes()
        (generation / "MANIFEST.sha256").write_text(
            f"{hashlib.sha256(dump).hexdigest()}  {len(dump)}  database.dump\n"
        )
        target = self.root / "restore-target"

        result = self.restore(generation, target=target)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(target.is_dir())
        self.assertEqual(list(target.iterdir()), [])

    def test_rejects_a_non_empty_target(self):
        self.install_fakes()
        generation = self.build_generation()
        target = self.root / "restore-target"
        target.mkdir()
        (target / "existing").write_text("x")

        result = self.restore(generation, target=target)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("empty", result.stderr)
        self.assertFalse(self.log.exists())

    def test_rejects_a_symlinked_target(self):
        self.install_fakes()
        generation = self.build_generation()
        real = self.root / "real-target"
        real.mkdir()
        target = self.root / "restore-target"
        os.symlink(real, target)

        result = self.restore(generation, target=target)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symbolic link", result.stderr)
        self.assertFalse(self.log.exists())

    def test_rejects_a_file_target(self):
        self.install_fakes()
        generation = self.build_generation()
        target = self.root / "restore-target"
        target.write_text("x")

        result = self.restore(generation, target=target)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a directory", result.stderr)
        self.assertFalse(self.log.exists())
