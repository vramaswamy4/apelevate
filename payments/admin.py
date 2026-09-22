from django.contrib import admin

from .models import TokenEntry, TokenPurchase


class ReadOnlyAdmin(admin.ModelAdmin):
    """Money records are written by payments.wallet only; the admin can look, not touch."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TokenPurchase)
class TokenPurchaseAdmin(ReadOnlyAdmin):
    list_display = ["user", "tokens", "amount_cents", "provider", "status", "created_at"]
    list_filter = ["status", "provider"]
    search_fields = ["user__email", "provider_order_id"]
    list_select_related = ["user"]


@admin.register(TokenEntry)
class TokenEntryAdmin(ReadOnlyAdmin):
    list_display = ["user", "delta", "kind", "created_at"]
    list_filter = ["kind"]
    search_fields = ["user__email"]
    list_select_related = ["user"]
