from django.conf import settings
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .bundles import BUNDLES, get_bundle
from .models import TokenPurchase
from .providers import PaymentProviderError, get_provider
from .services import PaymentVerificationError, complete_purchase, start_purchase


def _wants_json(request) -> bool:
    return "application/json" in request.headers.get("Accept", "")


def buy_tokens(request):
    provider = get_provider()
    purchases = request.user.token_purchases.all()[:10]
    return render(
        request,
        "payments/buy.html",
        {
            "bundles": BUNDLES,
            "purchases": purchases,
            "provider": provider,
            "paypal_client_id": settings.PAYPAL_CLIENT_ID if provider.name == "paypal" else "",
        },
    )


@require_POST
def checkout(request, bundle_key):
    bundle = get_bundle(bundle_key)
    if bundle is None:
        raise Http404
    try:
        purchase = start_purchase(request.user, bundle)
    except PaymentProviderError as exc:
        if _wants_json(request):
            return JsonResponse({"error": str(exc)}, status=502)
        messages.error(request, str(exc))
        return redirect("payments:buy")
    if _wants_json(request):  # PayPal's createOrder callback
        return JsonResponse({"orderID": purchase.provider_order_id, "purchaseId": purchase.pk})
    return redirect("payments:test_pay", pk=purchase.pk)


@require_POST
def capture(request, pk):
    purchase = get_object_or_404(TokenPurchase, pk=pk, user=request.user)
    try:
        complete_purchase(purchase)
    except (PaymentProviderError, PaymentVerificationError):
        message = "We couldn't confirm that payment, so no tokens were added."
        if _wants_json(request):
            return JsonResponse({"error": message}, status=402)
        messages.error(request, message)
        return redirect("payments:buy")
    url = reverse("payments:receipt", args=[purchase.pk])
    if _wants_json(request):  # PayPal's onApprove callback
        return JsonResponse({"redirect": url})
    return redirect(url)


def test_pay(request, pk):
    """The checkout page for the fake provider, so the full flow runs locally with no PayPal."""
    if not get_provider().is_test:
        raise Http404
    purchase = get_object_or_404(
        TokenPurchase, pk=pk, user=request.user, status=TokenPurchase.Status.CREATED
    )
    return render(request, "payments/test_pay.html", {"purchase": purchase})


def receipt(request, pk):
    purchase = get_object_or_404(TokenPurchase, pk=pk, user=request.user)
    return render(request, "payments/receipt.html", {"purchase": purchase})
