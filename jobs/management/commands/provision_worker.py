"""Issue a scoped worker credential and print its token once."""

from django.core.management.base import BaseCommand

from jobs.models import WorkerCredential


class Command(BaseCommand):
    help = "Issue a replaceable worker credential. The token is printed once."

    def add_arguments(self, parser):
        parser.add_argument("--label", default="laptop")

    def handle(self, *args, **options):
        credential, token = WorkerCredential.issue(options["label"])
        self.stdout.write(
            self.style.SUCCESS(f"worker credential {credential.pk} ({credential.label})")
        )
        self.stdout.write(token)
