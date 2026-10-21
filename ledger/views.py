"""Views for the ledger application."""

from datetime import date
from pathlib import Path

from django.db import transaction as transaction_db

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import DatabaseError
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.utils import timezone
from django.views.generic import DetailView, ListView, TemplateView

from intake.accept import accept_upload
from intake.inspect import FileTooLarge, IntakeRejected
from intake.storage import StorageUnavailable
from jobs.models import Job
from ledger.forms import UploadForm
from ledger.models import (
    Account,
    BalanceObservation,
    Correction,
    DuplicateMatch,
    Transaction,
    TransferLink,
    Upload,
)
from reporting.history import (
    account_balance_rows,
    chart_geometry,
    coverage_gaps,
    format_pence,
    net_cash_history,
)
from reporting.totals import (
    active_correction,
    classify,
    classify_source,
    compute_totals,
    classification_applies,
    effect_for_classification,
)
from reporting.transactions import METRIC_LABELS, PAGE_SIZE, metric_entries, search_transactions
from reporting.transfers import candidates_for

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


def _is_overlap_candidate(transaction, peer) -> bool:
    return (
        peer.pk != transaction.pk
        and peer.account_id == transaction.account_id
        and peer.posted_on == transaction.posted_on
        and peer.amount_pence == transaction.amount_pence
        and peer.description == transaction.description
        and peer.upload_id != transaction.upload_id
    )


def _describe_effect(effect) -> str:
    if effect is None:
        return "Unresolved: excluded from totals (provisional)"
    parts = []
    if effect.spending_pence:
        parts.append(f"spending {format_pence(effect.spending_pence)}")
    if effect.income_pence:
        parts.append(f"income {format_pence(effect.income_pence)}")
    if effect.cash_outgoing_pence:
        parts.append(f"cash outgoing {format_pence(effect.cash_outgoing_pence)}")
    return "; ".join(parts) if parts else "No spending, income or cash outgoing"


class ReviewListView(LoginRequiredMixin, TemplateView):
    """Transactions needing a classification decision or already corrected."""

    template_name = "ledger/review_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = []
        transactions = (
            Transaction.objects.select_related("account", "upload")
            .prefetch_related("corrections")
            .order_by("-posted_on", "-pk")[:500]
        )
        for transaction in transactions:
            correction = active_correction(transaction)
            duplicate = transaction.duplicate_matches.exists()
            if transaction.needs_review or correction is not None or duplicate or classify(transaction) is None:
                if duplicate:
                    label = "Confirmed duplicate"
                elif correction is not None:
                    label = f"Corrected: {correction.get_classification_display()}"
                else:
                    label = "Unresolved"
                rows.append(
                    {
                        "transaction": transaction,
                        "corrected": correction is not None,
                        "label": label,
                    }
                )
        context["rows"] = rows
        return context


class ReviewDetailView(LoginRequiredMixin, View):
    template_name = "ledger/review_detail.html"

    def get(self, request, pk):
        return self._render(request, pk)

    def post(self, request, pk):
        transaction = get_object_or_404(
            Transaction.objects.select_related("account", "upload"), pk=pk
        )
        action = request.POST.get("action")
        if action == "duplicate":
            peer = get_object_or_404(Transaction, pk=request.POST.get("peer"))
            with transaction_db.atomic():
                locked = {
                    item.pk: item
                    for item in Transaction.objects.select_for_update().filter(
                        pk__in=[transaction.pk, peer.pk]
                    )
                }
                transaction = locked[transaction.pk]
                peer = locked[peer.pk]
                if not _is_overlap_candidate(transaction, peer):
                    return self._render(
                        request,
                        pk,
                        error="Those rows are not an overlap candidate.",
                        status=400,
                    )
                if DuplicateMatch.objects.filter(transaction=peer).exists():
                    return self._render(
                        request,
                        pk,
                        error=(
                            "That row is already confirmed as a duplicate; point the "
                            "decision at the canonical row instead."
                        ),
                        status=400,
                    )
                if DuplicateMatch.objects.filter(
                    transaction=transaction, duplicate_of=peer
                ).exists():
                    return redirect("ledger:review_detail", pk=pk)
                DuplicateMatch.objects.create(transaction=transaction, duplicate_of=peer)
                Transaction.objects.filter(pk__in=[transaction.pk, peer.pk]).update(
                    needs_review=False
                )
            return redirect("ledger:review_detail", pk=pk)
        if action == "link":
            peer_id = request.POST.get("peer")
            kind = request.POST.get("kind")
            with transaction_db.atomic():
                locked = list(
                    Transaction.objects.select_for_update()
                    .filter(pk__in=[transaction.pk, peer_id])
                    .order_by("pk")
                )
                if len(locked) != 2:
                    return self._render(
                        request, pk, error="That pairing no longer exists.", status=400
                    )
                left, right = locked
                if kind not in TransferLink.Kind.values:
                    return self._render(
                        request, pk, error="Unknown link kind.", status=400
                    )
                if TransferLink.objects.filter(
                    transaction_a_id__in=[left.pk, right.pk]
                ).exists() or TransferLink.objects.filter(
                    transaction_b_id__in=[left.pk, right.pk]
                ).exists():
                    return self._render(
                        request,
                        pk,
                        error="One of these entries already has a confirmed link.",
                        status=400,
                    )
                matches = [
                    candidate
                    for candidate in candidates_for(left)
                    if candidate["transaction"].pk == right.pk
                ]
                if not matches or matches[0]["kind"] != kind:
                    return self._render(
                        request,
                        pk,
                        error="That pairing is no longer a valid candidate.",
                        status=400,
                    )
                TransferLink.objects.create(
                    transaction_a_id=left.pk, transaction_b_id=right.pk, kind=kind
                )
                Transaction.objects.filter(pk__in=[left.pk, right.pk]).update(
                    needs_review=False
                )
            return redirect("ledger:review_detail", pk=pk)
        if action == "keep_both":
            transaction.needs_review = False
            transaction.save(update_fields=["needs_review"])
            return redirect("ledger:review_detail", pk=pk)
        if action == "revert":
            for correction in transaction.corrections.filter(reverted_at__isnull=True):
                correction.reverted_at = timezone.now()
                correction.save(update_fields=["reverted_at"])
            return redirect("ledger:review_detail", pk=pk)
        if action == "correct":
            classification = request.POST.get("classification")
            if classification not in Correction.Classification.values:
                return HttpResponseBadRequest("Unknown classification")
            if not classification_applies(classification, transaction):
                return self._render(
                    request,
                    pk,
                    error=(
                        "That classification does not match the source's signed "
                        "direction; no correction was saved."
                    ),
                    status=400,
                )
            with transaction_db.atomic():
                for correction in transaction.corrections.filter(
                    reverted_at__isnull=True
                ):
                    correction.reverted_at = timezone.now()
                    correction.save(update_fields=["reverted_at"])
                Correction.objects.create(
                    transaction=transaction,
                    classification=classification,
                    note=(request.POST.get("note") or "")[:1000],
                )
            return redirect("ledger:review_detail", pk=pk)
        return HttpResponseBadRequest("Unknown action")

    def _render(self, request, pk, error=None, status=200):
        transaction = get_object_or_404(
            Transaction.objects.select_related("account", "upload").prefetch_related(
                "corrections"
            ),
            pk=pk,
        )
        active = active_correction(transaction)
        options = [
            {
                "value": value,
                "label": label,
                "effect": (
                    _describe_effect(effect_for_classification(value, transaction))
                    if classification_applies(value, transaction)
                    else "Not applicable to this source's signed direction"
                ),
                "applicable": classification_applies(value, transaction),
            }
            for value, label in Correction.Classification.choices
        ]
        candidates = (
            Transaction.objects.select_related("account", "upload")
            .filter(
                account_id=transaction.account_id,
                posted_on=transaction.posted_on,
                amount_pence=transaction.amount_pence,
                description=transaction.description,
            )
            .exclude(pk=transaction.pk)
            .exclude(upload_id=transaction.upload_id)
            .order_by("pk")
        )
        return render(
            request,
            self.template_name,
            {
                "transaction": transaction,
                "overlap_candidates": candidates,
                "transfer_candidates": candidates_for(transaction),
                "duplicate_decision": transaction.duplicate_matches.first(),
                "corrections": transaction.corrections.all(),
                "active_correction": active,
                "machine_effect": _describe_effect(classify_source(transaction)),
                "options": options,
                "correction_error": error,
            },
            status=status,
        )


class MetricDrilldownView(LoginRequiredMixin, TemplateView):
    """Rows contributing to one dashboard metric, with period context."""

    template_name = "ledger/metric.html"

    def get(self, request, *args, **kwargs):
        if request.GET.get("metric", "spending") not in METRIC_LABELS:
            return HttpResponseBadRequest("Unknown metric")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        metric = self.request.GET.get("metric", "spending")
        period_start, period_end, period_error = _selected_period(self.request)
        entries, total, exclusions = metric_entries(metric, period_start, period_end)
        page = Paginator(entries, PAGE_SIZE).get_page(self.request.GET.get("page"))
        context.update(
            {
                "metric": metric,
                "metric_label": METRIC_LABELS[metric],
                "period_start": period_start,
                "period_end": period_end,
                "period_error": period_error,
                "page": page,
                "total_display": format_pence(total),
                "exclusions": exclusions,
                "period_query": (
                    f"start={period_start.isoformat()}&end={period_end.isoformat()}"
                ),
            }
        )
        return context


class SearchView(LoginRequiredMixin, TemplateView):
    """Simple original-description search with optional period scoping."""

    template_name = "ledger/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = (self.request.GET.get("q") or "").strip()
        period_start = period_end = None
        if query:
            start = self.request.GET.get("start")
            end = self.request.GET.get("end")
            if start and end:
                try:
                    period_start = date.fromisoformat(start)
                    period_end = date.fromisoformat(end)
                except ValueError:
                    period_start = period_end = None
            rows = search_transactions(query, period_start, period_end)
            context["page"] = Paginator(rows, PAGE_SIZE).get_page(
                self.request.GET.get("page")
            )
        context["query"] = query
        context["period_start"] = period_start
        context["period_end"] = period_end
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
