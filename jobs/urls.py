"""URLs for job controls and the worker API."""

from django.urls import path

from jobs import api, views

app_name = "jobs"

urlpatterns = [
    path("uploads/process-now/", views.process_now, name="process_now"),
    path("api/worker/claims/", api.claim, name="claim"),
    path("api/worker/advice/claims/", api.claim_advice, name="claim_advice"),
    path(
        "api/worker/advice/<int:pk>/result/",
        api.advice_result,
        name="advice_result",
    ),
    path("api/worker/jobs/<int:job_id>/source/", api.source, name="source"),
    path("api/worker/jobs/<int:job_id>/heartbeat/", api.heartbeat, name="heartbeat"),
    path("uploads/<int:pk>/retry/", views.retry_job, name="retry"),
    path("api/worker/jobs/<int:job_id>/progress/", api.progress, name="progress"),
    path("api/worker/jobs/<int:job_id>/result/", api.result, name="result"),
]
