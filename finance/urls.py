from django.conf.urls import url

from finance.views import PaymentViewSet, WalletViewSet, PaymentVerificationAPIView, PaymentVerification, InstantPayment

wallet_view = WalletViewSet.as_view({'post': 'create', 'get': 'get'})

urlpatterns = [
    url(r'wallet/$', wallet_view, name='wallet'),
    url(r'payment/(?P<invoice_number>.*)/(?P<gateway>.*)/$', PaymentViewSet.as_view(), name='payment'),
    url(r'payment/verify/$', PaymentVerificationAPIView.as_view(), name='payment-verify-api'),
    url(r'VerifyPayment$', PaymentVerification.as_view(), name='payment-verify'),
    url(r'pay/(?P<invoice_number>.*)/(?P<gateway>.*)/$', InstantPayment.as_view(), name='instant-payment'),
]
