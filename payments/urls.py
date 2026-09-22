from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("", views.buy_tokens, name="buy"),
    path("checkout/<slug:bundle_key>/", views.checkout, name="checkout"),
    path("purchases/<int:pk>/", views.receipt, name="receipt"),
    path("purchases/<int:pk>/capture/", views.capture, name="capture"),
    path("purchases/<int:pk>/test-checkout/", views.test_pay, name="test_pay"),
]
