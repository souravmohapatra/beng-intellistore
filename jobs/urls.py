"""URLs for job controls and the worker API."""

from django.urls import path

from jobs import api, views

app_name = "jobs"

urlpatterns = [
    path("uploads/process-now/", views.process_now, name="process_now"),
    path("api/worker/claims/", api.claim, name="claim"),
    path("api/worker/jobs/<int:job_id>/source/", api.source, name="source"),
    path("api/worker/jobs/<int:job_id>/progress/", api.progress, name="progress"),
    path("api/worker/jobs/<int:job_id>/result/", api.result, name="result"),
]
