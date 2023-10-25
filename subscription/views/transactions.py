from django.db.models import Sum, Count, Q, Case, When, F, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from lib.paginations import TransactionPagination
from lib.query_handler import generate_date_cases
from subscription.filters import SubscriptionTransactionFilter, TargetTransactionFilter, \
    SubscriptionPeymanTransactionFilter, BaseTransactionFilter
from business.models import Business, Target
from subscription.models import BaseTransaction, Subscription
from subscription.models.transactions import TargetTransaction, SubscriptionPeymanTransaction
from subscription.models.transactions import SubscriptionTransaction
from subscription.serializers.transactions import BaseTransactionSerializer, BusinessTransactionSerializer, \
    TargetTransactionListSerializer, BaseTransactionPanelSerializer, BusinessPeymanTransactionSerializer, \
    BusinessAllTransactionsSerializer
from utils.filters import PersianFilterBackend
from utils.time import get_start_day_of_month


class TransactionsListAPIView(ListAPIView):
    """Return List paginated data for all user transactions"""
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    pagination_class = TransactionPagination
    serializer_class = BaseTransactionSerializer
    queryset = BaseTransaction.objects.select_related(
        'target_transaction', 'subscription_transaction', 'payment',  'subscription_peyman_transaction'
    ).all().order_by('-id')
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ('amount', 'transaction_type', 'created_time')

    def get_queryset(self):
        paid_invoices = Q(payment__is_paid=True)
        target_invoices = Q(transaction_type=10, target_transaction__is_paid=True)
        subscription_invoices = Q(transaction_type=15, subscription_transaction__status__in=[5, 10])
        peyman_subscription_invoices = Q(transaction_type=25, subscription_peyman_transaction__status__in=[5, 10])
        return self.queryset.filter(user=self.request.user).filter(
            subscription_invoices | paid_invoices | target_invoices | peyman_subscription_invoices
        )


class DonorsTransactionListAPIView(ListAPIView):
    """Return List paginated data for all business transactions"""
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    pagination_class = TransactionPagination
    serializer_class = BusinessTransactionSerializer
    filter_backends = (filters.OrderingFilter, DjangoFilterBackend, PersianFilterBackend,)
    filter_class = SubscriptionTransactionFilter
    ordering_fields = ('subscription__user__last_name', 'transaction__amount', 'status')
    search_fields = ('subscription__user__first_name', 'subscription__user__last_name')

    def get_queryset(self):
        return SubscriptionTransaction.objects.select_related(
            'subscription', 'transaction'
        ).filter(subscription__business=self.request.user.business).exclude(status=0).order_by('-id')


class DonorsTransactionListAPIViewV2(ListAPIView):
    """Return List paginated data for all business transactions"""
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    pagination_class = TransactionPagination
    serializer_class = BusinessPeymanTransactionSerializer
    filter_backends = (filters.OrderingFilter, DjangoFilterBackend, PersianFilterBackend,)

    filter_class = SubscriptionPeymanTransactionFilter
    ordering_fields = ('subscription__user__last_name', 'transaction__amount', 'status')
    search_fields = ('subscription__user__first_name', 'subscription__user__last_name')

    def get_queryset(self):
        return SubscriptionPeymanTransaction.objects.select_related(
            'subscription', 'transaction'
        ).filter(subscription__business=self.request.user.business).exclude(status=0).order_by('-id')


class DonorsTransactionListAPIViewV3(ListAPIView):
    """Return List paginated data for all user transactions"""
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    pagination_class = TransactionPagination
    serializer_class = BusinessAllTransactionsSerializer
    filter_class = BaseTransactionFilter
    filter_backends = (filters.OrderingFilter, DjangoFilterBackend, PersianFilterBackend,)
    ordering_fields = ('amount', 'transaction_type')
    search_fields = ('user__first_name', 'user__last_name')

    def get_queryset(self):
        subscription_invoices = Q(transaction_type=15, subscription_transaction__status__in=[5, 10])
        peyman_subscription_invoices = Q(transaction_type=25, subscription_peyman_transaction__status__in=[10, 20])

        return BaseTransaction.objects.select_related('subscription_peyman_transaction', 'subscription_transaction')\
            .filter(
            Q(subscription_peyman_transaction__subscription__business=self.request.user.business) |
            Q(subscription_transaction__subscription__business=self.request.user.business)
        ).filter(
            peyman_subscription_invoices | subscription_invoices
        ).order_by('-id')


class DonorsTransactionReportAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    pagination_class = TransactionPagination

    def get(self, request, *args, **kwargs):
        # all_transacion
        start_day_of_month = get_start_day_of_month(timezone.now())
        all_transactions = SubscriptionTransaction.objects.filter(subscription__business=request.user.business)
        all_direct_debit_transactions = SubscriptionPeymanTransaction.objects.filter(
            subscription__business=request.user.business
        )

        transactions = all_transactions.filter(paid_date__gte=start_day_of_month)
        direct_debit_transactions = all_direct_debit_transactions.filter(paid_date__gte=start_day_of_month)
        subscriptions = Subscription.objects.filter(business=request.user.business, is_enable=True)
        # target transaction
        targets = Target.objects.filter(business=request.user.business)
        target_transaction = TargetTransaction.objects.filter(
            target__business=request.user.business, is_paid=True, )
        # data
        data = {
            # total_income:
            'total_income': all_transactions.filter(status=10).aggregate(t=Coalesce(Sum('transaction__amount'), 0))[
                                't'] + all_direct_debit_transactions.filter(status=10).aggregate(
                t=Coalesce(Sum('transaction__amount'), 0)
            )['t'],
            'month_income': transactions.filter(status=10).aggregate(t=Coalesce(Sum('transaction__amount'), 0))['t'] +
                            direct_debit_transactions.filter(status=10).aggregate(
                                t=Coalesce(Sum('transaction__amount'), 0))['t'],
            'total_owed': all_transactions.filter(status=5).aggregate(t=Coalesce(Sum('transaction__amount'), 0))['t'],
            'paid_ratio': 0,
            # projects_income:
            'projects_count': targets.count(),
            'projects_income_count': target_transaction.count(),
            'total_project_income': target_transaction.aggregate(t=Coalesce(Sum('transaction__amount'), 0))['t'],
            'projet_paid_ratio': 0,
        }
        if subscriptions.count():
            data['paid_ratio'] = subscriptions.values('user').aggregate(
                t=Coalesce(Sum('tier__amount'), 0) / Coalesce(Count('user', distinct=True), 1))['t']
        if targets.count():
            data['projet_paid_ratio'] = target_transaction.aggregate(
                t=Coalesce(Sum('transaction__amount'), 0) / Coalesce(Count('id'), 1))['t']
        return Response(data)


class TransactionsChartAPIView(APIView):
    """Return chart data of subscribers transaction in content provider panel"""
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)

    def get(self, request, *args, **kwargs):
        cases = generate_date_cases()
        subscriptions = Subscription.objects.filter(
            business=request.user.business, is_enable=True
        ).annotate(month=cases).values('month').annotate(total=Sum('tier__amount'), count=Count('id'))
        return Response(subscriptions)


class TargetTransactionListAPIView(ListAPIView):
    serializer_class = TargetTransactionListSerializer
    pagination_class = TransactionPagination
    filter_backends = (filters.OrderingFilter, DjangoFilterBackend, PersianFilterBackend,)
    filter_class = TargetTransactionFilter
    ordering_fields = ('transaction__user__last_name', 'transaction__amount', 'is_paid')
    search_fields = ('transaction__user__first_name', 'transaction__user__last_name')
    authentication_classes = (
        JSONWebTokenAuthentication,
        SessionAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
    )

    def get_queryset(self):
        return TargetTransaction.objects.filter(
            target__business=self.request.user.business,
            is_paid=True, ).order_by('-id')
