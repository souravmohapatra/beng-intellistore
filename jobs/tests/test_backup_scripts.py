"""Behavioral tests for the containerized backup and restore scripts."""

import hashlib
import os
from pathlib import Path
import stat
import subprocess
import tempfile
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
