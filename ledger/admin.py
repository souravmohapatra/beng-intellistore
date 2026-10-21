"""Admin registration for authoritative records."""

from django.contrib import admin

from ledger.models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "created_at")
    list_filter = ("kind",)
    search_fields = ("name",)
