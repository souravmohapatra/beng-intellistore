"""Views for the ledger application."""

from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import DatabaseError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.utils import timezone
from django.views.generic import DetailView, ListView

from intake.accept import accept_upload
from intake.inspect import FileTooLarge, IntakeRejected
from intake.storage import StorageUnavailable
from jobs.models import Job
from ledger.forms import UploadForm
from ledger.models import Account, BalanceObservation, Transaction, Upload
from reporting.history import (
    account_balance_rows,
    chart_geometry,
    coverage_gaps,
    format_pence,
    net_cash_history,
)
from reporting.totals import compute_totals

LAST_ACCOUNT_SESSION_KEY = "intake.last_account_id"
LAST_SAVINGS_SESSION_KEY = "intake.savings_by_primary_account"


class AccountOverview(LoginRequiredMixin, ListView):
    """Private overview of named accounts and dashboard slots."""

    template_name = "ledger/overview.html"
    context_object_name = "accounts"

    def get_queryset(self):
        return Account.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period_start, period_end, period_error = _selected_period(self.request)
        report = compute_totals(period_start, period_end)
        points = net_cash_history(period_start, period_end)
        context.update(
            {
                "report": report,
                "period_error": period_error,
                "spending_display": format_pence(report.spending_pence),
                "income_display": format_pence(report.income_pence),
                "cash_outgoing_display": format_pence(report.cash_outgoing_pence),
                "net_cash_display": (
                    None
                    if report.net_cash_pence is None
                    else format_pence(report.net_cash_pence)
                ),
                "history_points": [
                    {
                        "observed_on": point.observed_on,
                        "net_cash_display": format_pence(point.net_cash_pence),
                        "disputed": point.disputed,
                    }
                    for point in points
                ],
                "history_chart": chart_geometry(points, period_start, period_end),
                "coverage_gaps": coverage_gaps(period_start, period_end),
                "balance_rows": [
                    {
                        **row,
                        "amount_display": (
                            None
                            if row["observation"] is None
                            else format_pence(row["observation"].amount_pence)
                        ),
                    }
                    for row in account_balance_rows(period_end)
                ],
            }
        )
        return context


def _selected_period(request):
    """Resolve month/year/custom selection, falling back to twelve months."""
    today = timezone.localdate()
    default_end = today
    try:
        anniversary = today.replace(year=today.year - 1)
    except ValueError:  # 29 February: clamp to 28 February, giving 1 March.
        anniversary = today.replace(year=today.year - 1, day=28)
    default_start = anniversary + timezone.timedelta(days=1)

    month = request.GET.get("month")
    year = request.GET.get("year")
    start = request.GET.get("start")
    end = request.GET.get("end")

    try:
        if month:
            first = _parse_iso(f"{month}-01")
            last = (first.replace(day=28) + timezone.timedelta(days=4)).replace(day=1) - timezone.timedelta(days=1)
            return first, last, None
        if year:
            year_value = int(year)
            return date(year_value, 1, 1), date(year_value, 12, 31), None
        if start or end:
            if not start or not end:
                raise ValueError("both dates are required")
            first = _parse_iso(start)
            last = _parse_iso(end)
            if first > last:
                raise ValueError("the start date is after the end date")
            return first, last, None
    except (ValueError, TypeError):
        return (
            default_start,
            default_end,
            "Those dates are not a valid period; showing the last twelve months.",
        )
    return default_start, default_end, None


def _parse_iso(value: str) -> date:
    from datetime import date as date_type

    return date_type.fromisoformat(value)


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
            remembered = dict(request.session.get(LAST_SAVINGS_SESSION_KEY, {}))
            remembered[str(account.pk)] = savings.pk
            request.session[LAST_SAVINGS_SESSION_KEY] = remembered
        return redirect("ledger:upload_detail", pk=upload.pk)

    @staticmethod
    def _initial(request):
        initial = {}
        account_id = request.session.get(LAST_ACCOUNT_SESSION_KEY)
        if account_id and Account.objects.filter(pk=account_id).exists():
            initial["account"] = account_id
        remembered = request.session.get(LAST_SAVINGS_SESSION_KEY, {})
        savings_id = remembered.get(str(initial.get("account"))) if initial.get("account") else None
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
