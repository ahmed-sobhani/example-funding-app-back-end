from django.db.models import Q
from django.http import Http404
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import mixins, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.exceptions import ValidationError

from finance.models import Payment, Gateway
from finance.serializers import PaymentInlineSerializer, WalletChargeSerializer \
    , PaymentSerializer
from subscription.models import BaseTransaction

import datetime


class InstantPayment(APIView):
    def get(self, request, invoice_number, gateway, *args, **kwargs):
        payment_query = dict(invoice_number=invoice_number)
        gateway_query = dict(gateway_code=gateway)
        payment = get_object_or_404(Payment.objects.all(), **payment_query)
        if payment.is_paid:
            payment = payment.clone()

        #if payment.gateway is not None:
            """ If user click twice and is case of when first request is in progress
            and second request come, backend should ignore second to prevent misleading
            but the problem is when a user click on payment and don't complete the process
            cannot do it again. This issue should be fixed later"""
        #    return Response(status=status.HTTP_204_NO_CONTENT)

        now = datetime.datetime.now()
        if now.hour == 23 and now.minute >= 45 or now.hour == 0 and now.minute < 30:
            raise ValidationError("Please try again after 00:30")

        gateway = get_object_or_404(Gateway.objects.filter(is_enable=True), **gateway_query)
        payment.gateway = gateway
        payment.save()

        bank_page = payment.bank_page
        if bank_page is None:
            return Response(
                {'message': _("An error occurred please try again later")},
                status=status.HTTP_400_BAD_REQUEST
            )

        return redirect(bank_page)


class PaymentViewSet(APIView):
    """
    Base payment handler API which do the following steps in separate GET/POST
    requests:
        - POST:
            - get invoice_uuid and gateway_code
            - set gateway for the invoice and save it
            - create redirect to the bank page according to the gateway

        - GET :
            - Find proper payment and related gateway
            - Verify given payment with provided gateway

    """
    serializer_class = PaymentInlineSerializer

    def get(self, request, invoice_number, gateway, *args, **kwargs):
        payment_query = dict(invoice_number=invoice_number)
        payment = get_object_or_404(Payment.objects.all(), **payment_query)

        now = datetime.datetime.now()
        if now.hour == 23 and now.minute >= 45 or now.hour == 0 and now.minute < 30:
            raise ValidationError("Please try again after 00:30")

        payment.verify()
        serializer = PaymentInlineSerializer(payment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, invoice_number, gateway, *args, **kwargs):
        payment_query = dict(invoice_number=invoice_number)
        gateway_query = dict(gateway_code=gateway)
        payment = get_object_or_404(Payment.objects.all(), **payment_query)
        gateway = get_object_or_404(Gateway.objects.filter(is_enable=True), **gateway_query)

        now = datetime.datetime.now()
        if now.hour == 23 and now.minute >= 45 or now.hour == 0 and now.minute < 30:
            raise ValidationError("Please try again after 00:30")

        payment.gateway = gateway
        payment.save()
        bank_page = payment.bank_page
        if bank_page is None:
            return Response(
                {'message': _("An error occurred please try again later")},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response({'url': bank_page}, status=status.HTTP_200_OK)


class PaymentVerificationAPIView(APIView):
    """Only check payment verification"""

    def get_payment(self):
        filter_data = dict()
        if 'Authority' in self.request.GET:
            filter_data['authority'] = self.request.GET.get('Authority')

        elif 'orderId' in self.request.data:
            filter_data['invoice_number'] = self.request.data.get('orderId')

        else:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        payment = get_object_or_404(Payment.objects.all(), **filter_data)
        return payment

    def get(self, request, *args, **kwargs):
        payment = self.get_payment()
        payment.verify(request.data)
        serializer = PaymentSerializer(payment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentVerification(View):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in ['get', 'post']:
            handler = self.default_handler
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)

    def get_data(self, request):
        if 'Authority' in request.GET:
            data = request.GET
        elif 'OrderId' in request.POST:
            data = request.POST
        elif hasattr(request, 'form') and 'OrderId' in request.form:
            data = request.form
        else:
            data = {}
        return data

    def get_payment(self, data):
        filter_data = dict()
        if 'Authority' in data:
            filter_data['authority'] = data.get('Authority')
        elif 'OrderId' in data:
            filter_data['id'] = data.get('OrderId')
        else:
            raise Http404
        payment = Payment.objects.select_related('transaction').filter(**filter_data).first()
        return payment

    def default_handler(self, request, *args, **kwargs):
        data = self.get_data(request)
        payment = self.get_payment(data)
        if payment is None:
            raise Http404
        payment.verify(data)
        if hasattr(payment.transaction, 'subscription_transaction'):
            template = "GreetingPaymentVerificationTemplate.html"
        elif hasattr(payment.transaction, 'target_transaction'):
            template = 'GreetingPaymentVerificationTemplateTargetTransaction.html'
        else:
            template = "PaymentVerificationTemplate.html"
        return render(request, template, {'payment': payment, 'user': request.user})


class WalletViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    """
    Return list of all wallet charge requests on GET request
    Create new wallet charge on POST requests
    """
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = WalletChargeSerializer
    queryset = BaseTransaction.objects.select_related(
        'target_transaction', 'subscription_transaction', 'payment'
    ).all().order_by('-id')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        paid_invoices = Q(payment__is_paid=True)
        target_invoices = Q(transaction_type=10, target_transaction__is_paid=True)
        subscription_invoices = Q(transaction_type=15, subscription_transaction__status__in=[5, 10])
        return self.queryset.filter(user=self.request.user).filter(
            subscription_invoices | paid_invoices | target_invoices)

    def get_object(self):
        query = {
            'payment__invoice_number': self.request.GET['invoice'],
            'user': self.request.user
        }
        obj = get_object_or_404(BaseTransaction, **query)
        return obj

    def get(self, request, *args, **kwargs):
        if 'invoice' in request.GET:
            return self.retrieve(request, *args, **kwargs)
        return self.list(request, *args, **kwargs)
