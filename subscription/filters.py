import django_filters

from django.db.models import Q

from subscription.models import Relation
from subscription.models.transactions import SubscriptionTransaction, TargetTransaction, SubscriptionPeymanTransaction,\
    BaseTransaction


class BaseTransactionFilter(django_filters.FilterSet):
    start_time = django_filters.DateFilter(field_name="created_time", lookup_expr='gte')
    end_time = django_filters.DateFilter(field_name="created_time", lookup_expr='lte')
    purpose = django_filters.CharFilter(field_name="purpose", method='purpose_filter')
    tier = django_filters.CharFilter(field_name="tier", method='tier_filter')
    status = django_filters.CharFilter(field_name="status", method='status_filter')

    class Meta:
        model = BaseTransaction
        fields = ['transaction_type', 'amount']

    def purpose_filter(self, queryset, name, value):
        sub_type = Q(transaction_type=BaseTransaction.SUBSCRIPTION)
        direct_debit_type = Q(transaction_type=BaseTransaction.DIRECT_DEBIT)
        all_transactions = queryset.filter(sub_type | direct_debit_type).filter(
            Q(subscription_transaction__subscription_purpose=value) |
            Q(subscription_peyman_transaction__subscription_purpose=value)
        )
        return all_transactions

    def tier_filter(self, queryset, name, value):
        sub_type = Q(transaction_type=BaseTransaction.SUBSCRIPTION)
        direct_debit_type = Q(transaction_type=BaseTransaction.DIRECT_DEBIT)
        all_transactions = queryset.filter(sub_type | direct_debit_type).filter(
            Q(subscription_transaction__subscription__tier=value) |
            Q(subscription_peyman_transaction__subscription__tier=value)
        )
        return all_transactions

    def status_filter(self, queryset, name, value):
        sub_type = Q(transaction_type=BaseTransaction.SUBSCRIPTION)
        direct_debit_type = Q(transaction_type=BaseTransaction.DIRECT_DEBIT)
        all_transactions = queryset.filter(sub_type | direct_debit_type).filter(
            Q(subscription_transaction__status=value) |
            Q(subscription_peyman_transaction__status=value)
        )
        return all_transactions


class SubscriptionTransactionFilter(django_filters.FilterSet):
    start_time = django_filters.DateFilter(field_name="created_time", lookup_expr='gte')
    end_time = django_filters.DateFilter(field_name="created_time", lookup_expr='lte')

    class Meta:
        model = SubscriptionTransaction
        fields = ['status', 'transaction__amount', 'subscription__tier', 'subscription_purpose']


class SubscriptionPeymanTransactionFilter(django_filters.FilterSet):
    start_time = django_filters.DateFilter(field_name="created_time", lookup_expr='gte')
    end_time = django_filters.DateFilter(field_name="created_time", lookup_expr='lte')

    class Meta:
        model = SubscriptionPeymanTransaction
        fields = ['status', 'transaction__amount', 'subscription__tier', 'subscription_purpose']


class TargetTransactionFilter(django_filters.FilterSet):
    start_time = django_filters.DateFilter(field_name="created_time", lookup_expr='gte')
    end_time = django_filters.DateFilter(field_name="created_time", lookup_expr='lte')

    class Meta:
        model = TargetTransaction
        fields = ['is_paid', 'transaction__amount', 'target__title', ]


class RelationFilter(django_filters.FilterSet):
    start_time = django_filters.DateFilter(field_name="created_time", lookup_expr='gte')
    end_time = django_filters.DateFilter(field_name="created_time", lookup_expr='lte')

    class Meta:
        model = Relation
        fields = ['start_time', 'end_time']
