from django.conf import settings
from suds.client import Client


def zpal_request_handler(gateway, payment):
    client = Client(gateway.gateway_request_url)
    result = client.service.PaymentRequest(
        gateway.credentials['merchant_id'], payment.amount,
        payment.detail,
        payment.user.email, payment.user.phone_number,
        settings.BASE_PATH + '/finance/VerifyPayment',
    )
    if result.Status == 100:
        payment.authority = result.Authority
        payment.save()
        return 'https://www.zarinpal.com/pg/StartPay/' + result.Authority
    else:
        return None


def zpal_payment_checker(payment, *args, **kwargs):
    client = Client(payment.gateway.gateway_request_url)
    result = client.service.PaymentVerification(
        payment.gateway.credentials['merchant_id'],
        payment.authority, payment.amount
    )
    if result.Status in [100, 101]:
        payment.is_paid = True
        payment.ref_id = result.RefID
        payment.save()
    return payment.is_paid
