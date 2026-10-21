"""Give every existing upload a waiting job."""

from django.db import migrations


def create_jobs(apps, schema_editor):
    Upload = apps.get_model("ledger", "Upload")
    Job = apps.get_model("jobs", "Job")
    for upload_id in Upload.objects.values_list("pk", flat=True):
        if not Job.objects.filter(upload_id=upload_id).exists():
            Job.objects.create(upload_id=upload_id, status="waiting")


def remove_jobs(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    Job.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_jobs, remove_jobs),
    ]
