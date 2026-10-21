"""URL routing for the ledger application."""

from django.urls import path

from ledger import views

app_name = "ledger"

urlpatterns = [
    path("", views.AccountOverview.as_view(), name="overview"),
]
