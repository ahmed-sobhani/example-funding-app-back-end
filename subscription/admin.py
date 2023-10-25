from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from import_export import resources
from import_export.admin import ExportMixin
from import_export.fields import Field
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Case, When
from itertools import chain
from django.db.models.functions import Trunc
from django.db.models import DateTimeField, Subquery
import pytz
from finance.models import Payment
from lib.common_admin import BaseAdmin
from subscription.models import Subscription, DiscountCode, BaseTransaction, Relation
from subscription.models.transactions import SubscriptionTransaction, TargetTransaction, SubscriptionPeymanTransaction
from utils.time import convert_to_jalali


class SubscriptionTransactionResource(resources.ModelResource):
    paid_date = Field()
    status = Field()
    due_date = Field()
    paid_month = Field()

    class Meta:
        model = SubscriptionTransaction
        fields = (
            'subscription__business__name', 'subscription__tier__title', 'subscription_purpose__title',
            'transaction__amount', 'transaction__user__phone_number'
        )

    def dehydrate_paid_date(self, subs):
        if subs.paid_date:
            return convert_to_jalali(subs.paid_date)
        return ''

    def dehydrate_paid_month(self, subs):
        if subs.paid_date:
            jalali = convert_to_jalali(subs.paid_date)
            return "{}/{}".format(jalali.year, jalali.month)
        return ''

    def dehydrate_due_date(self, subs):
        return subs.jalali_created_time

    def dehydrate_status(self, subs):
        return subs.get_status_display()


class TargetTransactionResource(resources.ModelResource):
    paid_date = Field()
    paid_month = Field()

    class Meta:
        model = TargetTransaction
        fields = (
            'target__business__name', 'target__title','transaction__amount', 'transaction__user__phone_number'
        )

    def dehydrate_paid_date(self, subs):
        return convert_to_jalali(subs.created_time)

    def dehydrate_paid_month(self, subs):
        jalali = convert_to_jalali(subs.created_time)
        return "{}/{}".format(jalali.year, jalali.month)


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'subscriber', 'business', 'tier', 'jalali_created_time',
                    'jalali_due_day_of_month', 'is_enable', 'end_date', 'sub_type']
    list_filter = ['is_enable', 'jalali_due_day_of_month', 'sub_type']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']

    def subscriber(self, obj):
        return obj.user.get_full_name()


class WrongTransactionsFilter(SimpleListFilter):
    title = 'Wrong repeated transactions'
    parameter_name = 'wrong'

    def lookups(self, request, model_admin):
        return (
            ('true', 'wrong'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'true':
            all_transactions = queryset.filter(
                Q(created_time__hour__lte=0,
                    created_time__minute__lte=30,) |
                Q(created_time__hour__gte=23,
                    created_time__minute__gte=45)
                )
            transactions_list = list(all_transactions.values_list('id', flat=True))
            for transaction in all_transactions:
                user = transaction.transaction.user
                local_dt = transaction.created_time.astimezone(pytz.timezone('Asia/Tehran'))
                if local_dt.hour == 23:
                    tomorrow_transactions = queryset.filter(
                        created_time__year=local_dt.year,
                        created_time__month=local_dt.month,
                        transaction__user=user,
                        created_time__day=local_dt.day + 1,
                    )
                    if tomorrow_transactions.count() <= 0:
                        obj_index_id = transactions_list.index(transaction.id)
                        del transactions_list[obj_index_id]
                        all_transactions = all_transactions.filter(
                            pk__in=transactions_list
                        )
                    a, b = list(all_transactions.values_list('id', flat=True)),\
                        list(tomorrow_transactions.values_list('id', flat=True))
                    all_transactions = queryset.filter(id__in=a + b)

                if local_dt.hour == 0:
                    tomorrow_transactions = queryset.filter(
                        created_time__year=local_dt.year,
                        created_time__month=local_dt.month,
                        transaction__user=user,
                        created_time__day=local_dt.day,
                    )
                    if tomorrow_transactions.count() <= 1:
                        tomorrow_transactions_list = list(tomorrow_transactions.values_list('id', flat=True))
                        obj_index_id_tommorow = tomorrow_transactions_list.index(transaction.id)
                        obj_index_id = transactions_list.index(transaction.id)
                        del transactions_list[obj_index_id]
                        del tomorrow_transactions_list[obj_index_id_tommorow]
                        all_transactions = all_transactions.filter(pk__in=transactions_list)
                        tomorrow_transactions = tomorrow_transactions.filter(pk__in=tomorrow_transactions_list)
                    a, b = list(all_transactions.values_list('id', flat=True)), \
                        list(tomorrow_transactions.values_list('id', flat=True))
                    all_transactions = queryset.filter(id__in=a + b)
            return all_transactions


class SubscriptionTransactionAdmin(ExportMixin, BaseAdmin):
    extra_list_display = [
        'transaction', 'user', 'subscription', 'subscription_purpose', 'due_date', 'is_paid', 'paid_date', 'status'
    ]
    list_filter = ['status', WrongTransactionsFilter]
    search_fields = ['subscription__user__username', 'subscription__user__first_name', 'subscription__user__last_name',
                     'created_time']
    date_hierarchy = 'created_time'  # DateField
    resource_class = SubscriptionTransactionResource

    def user(self, obj):
        return obj.subscription.user.get_full_name()


class TargetTransactionAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ['transaction', 'get_transaction_user', 'target', 'is_paid']
    list_filter = ('is_paid',)
    # search_fields = ("user__phone_number", 'user__first_name', 'target__code')
    resource_class = TargetTransactionResource

    def get_transaction_user(self, obj):
        return obj.transaction.user
    get_transaction_user.short_description = "user"


class DiscountCodeAdmin(BaseAdmin):
    extra_list_display = ['user', 'business', 'post', 'used', 'code', 'used_time']

    def business(self, obj):
        return obj.post.business


class TargetTransactionInlineAdmin(admin.TabularInline):
    model = TargetTransaction
    extra = 0

    def has_add_permission(self, request):
        return False


class SubscriptionTransactionInlineAdmin(admin.TabularInline):
    model = SubscriptionTransaction
    extra = 0

    def has_add_permission(self, request):
        return False


class PaymentInlineAdmin(admin.TabularInline):
    model = Payment
    readonly_fields = ['is_paid']
    extra = 0

    def has_add_permission(self, request):
        return False


class BaseTransactionFilter(SimpleListFilter):
    title = 'combine direct-debit and bank approach'
    parameter_name = 'db'

    def lookups(self, request, model_admin):
        return (
            ('true', 'filter'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(transaction_type__in=[BaseTransaction.SUBSCRIPTION, BaseTransaction.DIRECT_DEBIT])


class BaseTransactionPaidFilter(SimpleListFilter):
    title = 'pay status'
    parameter_name = 'paid'

    def lookups(self, request, model_admin):
        return (
            ('true', 'paid'),
            ('false', 'not paid'),
        )

    def queryset(self, request, queryset):
        q = queryset.filter().annotate(paid_status=Case(
            When(
                subscription_peyman_transaction__isnull=False,
                then="subscription_peyman_transaction__is_paid"
            ),
            When(
                subscription_transaction__isnull=False,
                then="subscription_transaction__is_paid"
            ),
            When(
                target_transaction__isnull=False,
                then="target_transaction__is_paid"
            ),
            When(
                sms_package_transaction__isnull=False,
                then="sms_package_transaction__is_paid"
            ),
            When(
                follower_wallet_charge_transaction__isnull=False,
                then="follower_wallet_charge_transaction__is_paid"
            ),
            When(
                transaction_type=BaseTransaction.WALLET_CHARGE,
                then="payment__is_paid"
            ),
            When(
                transaction_type=BaseTransaction.INSTANT,
                then="payment__is_paid"
            ),
        ))
        if self.value() == 'true':
            return q.filter(paid_status=True)
        if self.value() == 'false':
            return q.filter(paid_status=False)


class TransactionAdmin(ExportMixin, BaseAdmin):
    extra_list_display = ['username', 'amount', 'transaction_type', 'is_paid', 'subscription_purpose']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    list_filter = ('transaction_type', BaseTransactionFilter, BaseTransactionPaidFilter)
    inlines = [TargetTransactionInlineAdmin, SubscriptionTransactionInlineAdmin, PaymentInlineAdmin]

    def username(self, obj):
        return obj.user.get_full_name()

    def subscription_purpose(self, obj):
        return obj.related.subscription_purpose if obj.related.subscription_purpose is not None else\
            obj.related.subscription.subscription_purpose

    username.short_description = "username"
    subscription_purpose.short_description = "purpose"


class RelationAdmin(admin.ModelAdmin):
    list_display = ['follower', 'full_name', 'following', 'description']
    search_fields = [
        'follower__username',
        'follower__first_name',
        'follower__last_name',
        'following__name',
    ]

    def full_name(self, obj):
        return obj.follower.get_full_name()


class SubscriptionPeymanTransactionAdmin(admin.ModelAdmin):
    list_filter = ('status',)


admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(DiscountCode, DiscountCodeAdmin)
admin.site.register(BaseTransaction, TransactionAdmin)
admin.site.register(SubscriptionTransaction, SubscriptionTransactionAdmin)
admin.site.register(TargetTransaction, TargetTransactionAdmin)
admin.site.register(Relation, RelationAdmin)
admin.site.register(SubscriptionPeymanTransaction, SubscriptionPeymanTransactionAdmin)
