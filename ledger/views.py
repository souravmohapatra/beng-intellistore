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
from intake.storage import StorageUnavailable
from ledger.forms import UploadForm
from ledger.models import Account, Upload


class AccountOverview(LoginRequiredMixin, ListView):
    """Private overview of named accounts and dashboard slots."""

    template_name = "ledger/overview.html"
    context_object_name = "accounts"

    def get_queryset(self):
        return Account.objects.all()


class UploadListView(LoginRequiredMixin, View):
    """List receipts and accept a new upload."""

    template_name = "ledger/uploads.html"

    def get(self, request):
        return self._render(request, UploadForm())

    def post(self, request):
        form = UploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return self._render(request, form)

        submitted = form.cleaned_data["file"]
        try:
            upload = accept_upload(
                account=form.cleaned_data["account"],
                filename=submitted.name,
                data=submitted.read(),
                content_type=submitted.content_type,
            )
        except StorageUnavailable:
            return self._render(
                request,
                form,
                status=503,
                storage_error="The original could not be preserved. Nothing was accepted.",
            )
        except DatabaseError:
            return self._render(
                request,
                form,
                status=503,
                storage_error=(
                    "The receipt could not be recorded. The source bytes were preserved; "
                    "please retry."
                ),
            )
        return redirect("ledger:upload_detail", pk=upload.pk)

    def _render(self, request, form, status=200, storage_error=None):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "uploads": Upload.objects.select_related("account", "original"),
                "storage_error": storage_error,
            },
            status=status,
        )


class UploadDetailView(LoginRequiredMixin, DetailView):
    template_name = "ledger/upload_detail.html"
    context_object_name = "upload"

    def get_queryset(self):
        return Upload.objects.select_related("account", "original")


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
