"""Forms for upload intake."""

from django import forms

from ledger.models import Account


class UploadForm(forms.Form):
    account = forms.ModelChoiceField(
        queryset=Account.objects.order_by("name"),
        label="Named account",
    )
    file = forms.FileField(
        label="Statement file",
        error_messages={"required": "Choose a statement file."},
    )
