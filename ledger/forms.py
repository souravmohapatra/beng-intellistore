"""Forms for named-account onboarding and upload intake."""

from django import forms

from ledger.models import Account, AccountKind


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ("name", "kind")
        labels = {"name": "Account name", "kind": "Account type"}
        help_texts = {
            "name": "Use a name you recognise, not an account number.",
            "kind": "Choose the type shown by your bank; credit-card balances are debt.",
        }


class UploadForm(forms.Form):
    account = forms.ModelChoiceField(
        queryset=Account.objects.order_by("name"),
        label="Named account",
    )
    savings_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(kind=AccountKind.SAVINGS).order_by("name"),
        label="Savings account (consolidated statements)",
        required=False,
        empty_label="None",
    )
    file = forms.FileField(
        label="Statement file",
        error_messages={"required": "Choose a statement file."},
    )
