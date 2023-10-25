import datetime
from django.db.models import Count
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.http import Http404
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView, ListCreateAPIView, get_object_or_404, CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from lib.paginations import PublicBusinessPagination
from lib.query_handler import generate_date_cases
from subscription.models import Subscription, BaseTransaction
from subscription.models.transactions import TargetTransaction
from subscription.serializers import SubscriptionCreateSerializer
from subscription.serializers.subscriptions import SubscriptionListSerializer, SubscriberList, \
    RegisterUserWithTierSerializer
from subscription.serializers.transactions import TargetTransactionCreateSerializer
from subscription.tasks import send_register_user_by_business_sms
from user.models import User
from user.serializers import UserLightSerializer
from business.models import SubscriptionInvite

from business.permissions import HasBusiness

from finance.utils.zarinpal import zpal_request_handler
from finance.models import Gateway

from utils.encoder import IDEncoder
from utils.links import make_short

import requests


class SubscriptionListCreateAPIView(ListCreateAPIView):
    """
    Server site user requests when they want subscribe to specific tier of one
    provider
    """
    serializer_class = SubscriptionCreateSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return SubscriptionListSerializer
        return self.serializer_class

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user, is_enable=True)

    def put(self, request, *args, **kwargs):
        role = self.request.user.profile.role
        if role == 2 or role == 3:
            queryset = Subscription.objects.filter(is_enable=True)
        else:
            queryset = self.get_queryset()
        if not request.data.get('subscription'):
            return Response({"error": _("Subscription pk is not submitted")}, status=status.HTTP_400_BAD_REQUEST)
        filter_queryset = {'pk': request.data.get('subscription')}
        subscription = get_object_or_404(queryset, **filter_queryset)
        subscription.is_enable = False
        subscription.end_date = timezone.now()
        subscription.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscriberAPIView(APIView):
    """
    List last subscribers fot this & pre month.
    """
    def get(self, request, *args, **kwargs):
        subscribers_list = Subscription.objects.filter(
                        business__url_path=self.kwargs['slug'],
                        is_enable=True
                    ).order_by('user', '-created_time').values_list('user', flat=True)[:3]
        serializer = UserLightSerializer(User.objects.filter(pk__in=subscribers_list), many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SubscriptionChartAPIView(APIView):
    """Return chart data of subscribers in content provider panel"""
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)

    def get(self, request, *args, **kwargs):
        cases = generate_date_cases()
        subscriptions = Subscription.objects.filter(
            business=request.user.business
        ).annotate(month=cases).annotate(count=Count('month'))
        # TODO: Generate chart format data
        # return Response(subscriptions)
        return Response([
            {'month': 1, 'count': subscriptions.count(),
             'enable': subscriptions.filter(is_enable=True).count(),
             'disable': subscriptions.filter(is_enable=False).count()}
        ])


class SubscriptionTableListAPIView(ListAPIView):
    """Return table data of subscribers in content provider panel"""
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = SubscriberList
    pagination_class = PublicBusinessPagination

    def get_queryset(self):
        return Subscription.objects.filter(business=self.request.user.business, is_enable=True)


class TargetTransactionAPIView(ListCreateAPIView):
    """
    Create Target payment order or return a list of pre ordered payments
    """
    permission_classes = (IsAuthenticated, )
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = TargetTransactionCreateSerializer
    pagination_class = PublicBusinessPagination

    def get_queryset(self):
        return TargetTransaction.objects.filter(transaction__user=self.request.user)

    def get_serializer_class(self):
        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserValidationForSubscription(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)

    def get(self, request, *args, **kwargs):
        national_code = request.user.profile.national_code
        if national_code is not None and bool(national_code):
            return Response({"valid": True, 'national_code': national_code})
        return Response({'valid': False, 'national_code': national_code})


class SubscriptionInviteAPIView(APIView):
    def get(self, *args, **kwargs):
        pk = kwargs.get('slug', None)
        sub_invite = get_object_or_404(SubscriptionInvite, id=IDEncoder().decode_id(pk))
        user, create = User.objects.get_or_create(phone_number=sub_invite.contact_phone,
                                                  defaults={'date_joined': datetime.datetime.now()})
        if create:
            user.first_name = sub_invite.contact_name
            user.save()
        sub = Subscription.objects.create(user=user, tier=sub_invite.tier, business=sub_invite.business,
                                          sub_auto_pay=False)
        payment = sub.transactions.last().transaction.payment
        gateway = get_object_or_404(Gateway, is_enable=True, gateway_code=Gateway.FUNCTION_ZARRINPAL)
        pay_link = zpal_request_handler(gateway, payment)
        return redirect(pay_link)


class RegisterUserWithTierCreateAPIView(CreateAPIView):
    permission_classes = (IsAuthenticated, HasBusiness)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = RegisterUserWithTierSerializer

    def create(self, request, *args, **kwargs):
        serializer = RegisterUserWithTierSerializer(context={"request": request})
        data = serializer.create(request.data)

        link = make_short(data.transactions.first().transaction.payment.get_instant_link())[8:]
        phone = data.transactions.first().transaction.user.phone_number

        params = {
            "token": data.transactions.first().transaction.user.first_name,
            "token2": data.tier.title,
            "token3": link[8:],
        }

        send_register_user_by_business_sms.delay(phone, params)
        return Response({"pay_link": link})
