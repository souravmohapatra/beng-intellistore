"""Views for the ledger application."""

from pathlib import Path

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import DatabaseError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from intake.accept import accept_upload
from intake.inspect import FileTooLarge, IntakeRejected
from intake.storage import StorageUnavailable
from jobs.models import Job
from ledger.forms import UploadForm
from ledger.models import Account, BalanceObservation, Transaction, Upload

LAST_ACCOUNT_SESSION_KEY = "intake.last_account_id"
LAST_SAVINGS_SESSION_KEY = "intake.last_savings_account_id"


class AccountOverview(LoginRequiredMixin, ListView):
    """Private overview of named accounts and dashboard slots."""

    template_name = "ledger/overview.html"
    context_object_name = "accounts"

    def get_queryset(self):
        return Account.objects.all()


class AccountTransactionsView(LoginRequiredMixin, DetailView):
    """Committed transactions and balance anchors for one named account."""

    template_name = "ledger/account_transactions.html"
    context_object_name = "account"

    def get_queryset(self):
        return Account.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["transactions"] = Transaction.objects.filter(
            account=self.object
        ).select_related("upload")
        context["balances"] = BalanceObservation.objects.filter(account=self.object)
        return context


class UploadListView(LoginRequiredMixin, View):
    """List receipts and accept a new upload."""

    template_name = "ledger/uploads.html"

    def get(self, request):
        return self._render(request, UploadForm(initial=self._initial(request)))

    def post(self, request):
        form = UploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return self._render(request, form)

        submitted = form.cleaned_data["file"]
        account = form.cleaned_data["account"]
        try:
            upload = accept_upload(
                account=account,
                savings_account=form.cleaned_data.get("savings_account"),
                filename=submitted.name,
                data=submitted.read(),
            )
        except FileTooLarge as exc:
            return self._render(request, form, status=413, intake_error=str(exc))
        except IntakeRejected as exc:
            return self._render(request, form, status=400, intake_error=str(exc))
        except StorageUnavailable:
            return self._render(
                request,
                form,
                status=503,
                intake_error="The original could not be preserved. Nothing was accepted.",
            )
        except DatabaseError:
            return self._render(
                request,
                form,
                status=503,
                intake_error=(
                    "The receipt could not be recorded. The source bytes were preserved; "
                    "please retry."
                ),
            )

        request.session[LAST_ACCOUNT_SESSION_KEY] = account.pk
        savings = form.cleaned_data.get("savings_account")
        if savings is not None:
            request.session[LAST_SAVINGS_SESSION_KEY] = savings.pk
        return redirect("ledger:upload_detail", pk=upload.pk)

    @staticmethod
    def _initial(request):
        initial = {}
        account_id = request.session.get(LAST_ACCOUNT_SESSION_KEY)
        if account_id and Account.objects.filter(pk=account_id).exists():
            initial["account"] = account_id
        savings_id = request.session.get(LAST_SAVINGS_SESSION_KEY)
        if savings_id and Account.objects.filter(pk=savings_id).exists():
            initial["savings_account"] = savings_id
        return initial

    def _render(self, request, form, status=200, intake_error=None):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "uploads": Upload.objects.select_related("account", "original", "job"),
                "waiting_count": Job.objects.filter(status=Job.Status.WAITING).count(),
                "intake_error": intake_error,
            },
            status=status,
        )


class UploadDetailView(LoginRequiredMixin, DetailView):
    template_name = "ledger/upload_detail.html"
    context_object_name = "upload"

    def get_queryset(self):
        return Upload.objects.select_related("account", "original", "job").prefetch_related(
            "job__attempts__events", "job__attempts__result"
        )


class UploadOriginalView(LoginRequiredMixin, View):
    """Serve the preserved bytes of one accepted original."""

    def get(self, request, pk):
        upload = get_object_or_404(Upload.objects.select_related("original"), pk=pk)
        path = Path(settings.DATA_DIR) / upload.original.stored_path
        try:
            handle = open(path, "rb")
        except OSError as exc:
            raise Http404("Original is not available") from exc
        return FileResponse(
            handle,
            content_type=upload.original.content_type,
            as_attachment=False,
            filename=upload.filename,
        )
