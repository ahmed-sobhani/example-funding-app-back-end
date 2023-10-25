from django.conf import settings
from suds.client import Client


def parsian_request_handler(gateway, payment):
    client = Client(gateway.gateway_request_url)
    data = dict(
        LoginAccount=gateway.credentials['pin'], Amount=payment.amount*10,
        OrderId=payment.id, CallBackUrl=settings.BASE_PATH + '/finance/VerifyPayment',
        AdditionalData=''
    )
    result = client.service.SalePaymentRequest(requestData=data)
    response = {"token": getattr(result, 'Token', ''), "status": getattr(result, 'Status', ''), "message": getattr(result, 'Message', '')}
    payment.save_log(response, scope='result handler', save=True)
    if result.Status == 0 and result.Token > 0:
        payment.authority = result.Token
        payment.save()
        return "https://pec.shaparak.ir/NewIPG/?Token={}".format(result.Token)
    else:
        return None


def parsian_payment_checker(payment, data):
    payment.save_log(data, "Bank operation", save=True)
    client = Client(payment.gateway.gateway_verify_url)
    data = dict(LoginAccount=payment.gateway.credentials['pin'], Token=payment.authority)
    result = client.service.ConfirmPayment(requestData=data)
    response = {"token": getattr(result, 'Token', ''), "status": getattr(result, 'Status', ''), "RRn": getattr(result, 'RRN', 0), "card_number": getattr(result, '‫‪CardNumberMasked‬‬', '')}
    payment.save_log(response, "Payment checker", save=True)
    if result.Status == 0 and result.Token > 0:
        payment.is_paid = True
        payment.save()
    return payment.is_paid
