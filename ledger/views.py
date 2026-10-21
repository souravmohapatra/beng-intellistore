"""Views for the ledger application."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from ledger.models import Account


class AccountOverview(LoginRequiredMixin, ListView):
    """Private overview of named accounts and dashboard slots."""

    template_name = "ledger/overview.html"
    context_object_name = "accounts"

    def get_queryset(self):
        return Account.objects.all()
