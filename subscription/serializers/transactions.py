from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from django.utils.translation import ugettext_lazy as _

from business.serializers import TierLightSerializer, SubscriptionPurposeSerializer, TargetLightSerializer, BusinessLightSerializer
from finance.models import Payment
from finance.serializers import PaymentInlineSerializer
from subscription.models.transactions import SubscriptionTransaction, BaseTransaction, TargetTransaction, \
    SubscriptionPeymanTransaction
from subscription.serializers.subscriptions import SubscriptionDetailSerializer
from user.serializers import UserLightSerializer


class BaseTransactionInlineSerializer(serializers.ModelSerializer):
    """
    BaseTransaction readonly data serializer, is just used for single purpose,
    avoid to use in payment or invoice related serializers. It may cause
    unlimited recursive loops
    """
    payment = PaymentInlineSerializer()

    class Meta:
        model = BaseTransaction
        fields = ('user', 'amount', 'transaction_type', 'title', 'payment')


class OperatorChargeWalletTransactionSerializer(serializers.ModelSerializer):
    """
    BaseTransaction readonly data serializer, is just used for single purpose,
    avoid to use in payment or invoice related serializers. It may cause
    unlimited recursive loops
    """
    class Meta:
        model = BaseTransaction
        fields = ('user', 'amount',)


class SubscriptionInlineTransactionSerializer(serializers.ModelSerializer):
    """
    This serializer will not serialize BaseTransaction data to avoid redundant data
    """
    subscription = SubscriptionDetailSerializer()
    user = UserLightSerializer(source='transaction.user')
    subscription_purpose = serializers.CharField(source='subscription_purpose.title', allow_null=True)
    payment_link = serializers.SerializerMethodField()
    transaction_id = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionTransaction
        fields = (
           'transaction_id', 'subscription', 'user', 'due_date', 'is_paid', 'paid_date', 'payment_link', 'status',
           'subscription_purpose', 'created_time'
        )

    def get_transaction_id(self, obj):
        return obj.id

    def get_payment_link(self, obj):
        if not obj.is_paid:
            return obj.transaction.payment.get_instant_link()
        return None


class SubscriptionInlinePeymanTransactionSerializer(serializers.ModelSerializer):
    """
    This serializer will not serialize BaseTransaction data to avoid redundant data
    """
    subscription = SubscriptionDetailSerializer()
    user = UserLightSerializer(source='transaction.user')
    subscription_purpose = serializers.CharField(source='subscription_purpose.title', allow_null=True)

    class Meta:
        model = SubscriptionPeymanTransaction
        fields = (
            'subscription', 'user', 'due_date', 'is_paid', 'paid_date', 'status', 'subscription_purpose', 'created_time'
        )


class SubscriptionTransactionSerializer(serializers.ModelSerializer):
    """
    SubscriptionTransactionSerializer handle will be used inline when user
    wants to subscribe to a business and will be notified about transaction
    status or next step
    """
    transaction = BaseTransactionInlineSerializer()

    class Meta:
        model = SubscriptionTransaction
        fields = ('subscription', 'transaction', 'due_date', 'is_paid', 'paid_date', 'status', 'created_time')


class BusinessTransactionSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source='subscription.user.get_full_name')
    relation_id = serializers.SerializerMethodField()
    amount = serializers.IntegerField(source='transaction.amount')
    subscription_purpose = serializers.SerializerMethodField()
    tier = TierLightSerializer(source='subscription.tier')
    owed_payment_link = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionTransaction
        # TODO: Change modified_time to the paid_date later
        fields = (
            'id', 'fullname', 'relation_id', 'amount', 'tier', 'subscription_purpose', 'modified_time', 'status',
            'created_time', 'owed_payment_link'
        )

    def get_owed_payment_link(self, obj):
        if not obj.is_paid:
            return obj.transaction.payment.get_instant_link()
        return None

    def get_subscription_purpose(self, obj):
        if getattr(obj, 'subscription_purpose', None):
            return obj.subscription_purpose.title
        return None

    def get_relation_id(self, obj):
        # relation = obj.subscription.relation
        # if relation is not None:
        #     return relation.id
        # return None
        return obj.subscription.user.id


class BusinessAllTransactionsSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    fullname = serializers.CharField(source='user.get_full_name')
    relation_id = serializers.SerializerMethodField()
    tier = serializers.SerializerMethodField()
    subscription_purpose = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    owed_payment_link = serializers.SerializerMethodField()

    class Meta:
        model = BaseTransaction
        fields = (
            'id', 'fullname', 'relation_id', 'amount', 'tier', 'subscription_purpose', 'modified_time',
            'created_time', 'transaction_type', 'status', 'owed_payment_link'
        )

    def get_id(self, obj):
        if obj.transaction_type == obj.SUBSCRIPTION:
            return obj.subscription_transaction.id
        if obj.transaction_type == obj.DIRECT_DEBIT:
            return obj.subscription_peyman_transaction.id

    def get_status(self, obj):
        if obj.transaction_type == obj.SUBSCRIPTION:
            return obj.subscription_transaction.status
        if obj.transaction_type == obj.DIRECT_DEBIT:
            return obj.subscription_peyman_transaction.status

    def get_relation_id(self, obj):
        return obj.user.id

    def get_tier(self, obj):
        if obj.transaction_type == obj.SUBSCRIPTION:
            return TierLightSerializer(obj.subscription_transaction.subscription.tier).data
        if obj.transaction_type == obj.DIRECT_DEBIT:
            return TierLightSerializer(obj.subscription_peyman_transaction.subscription.tier).data

    def get_subscription_purpose(self, obj):
        # return obj.related.subscription_purpose if obj.related.subscription_purpose is not None else \
        #     obj.related.subscription.subscription_purpose
        if obj.transaction_type == BaseTransaction.SUBSCRIPTION and getattr(obj.subscription_transaction,
                                                                            'subscription_purpose', None) is not None:
            return obj.subscription_transaction.subscription.subscription_purpose.title

        if obj.transaction_type == BaseTransaction.DIRECT_DEBIT and getattr(obj.subscription_peyman_transaction,
                                                                            'subscription_purpose', None) is not None:
            return obj.subscription_peyman_transaction.subscription.subscription_purpose.title

        return None

    def get_owed_payment_link(self, obj):
        if obj.transaction_type == obj.SUBSCRIPTION:
            if not obj.subscription_transaction.is_paid:
                return obj.subscription_transaction.transaction.payment.get_instant_link()
        if obj.transaction_type == obj.DIRECT_DEBIT:
            if not obj.subscription_peyman_transaction.is_paid:
                return obj.subscription_peyman_transaction.transaction.payment.get_instant_link()
        return None


class BusinessPeymanTransactionSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source='subscription.user.get_full_name')
    relation_id = serializers.SerializerMethodField()
    amount = serializers.IntegerField(source='transaction.amount')
    subscription_purpose = serializers.SerializerMethodField()
    tier = TierLightSerializer(source='subscription.tier')

    class Meta:
        model = SubscriptionPeymanTransaction
        fields = (
            'fullname', 'relation_id', 'amount', 'tier', 'subscription_purpose', 'modified_time', 'status',
            'created_time'
        )

    def get_subscription_purpose(self, obj):
        if getattr(obj, 'subscription_purpose', None):
            return obj.subscription_purpose.title
        return None

    def get_relation_id(self, obj):
        # relation = obj.subscription.relation
        # if relation is not None:
        #     return relation.id
        # return None
        return obj.subscription.user.id

class BaseTransactionSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username')
    title = serializers.SerializerMethodField()
    payment = serializers.UUIDField(source='payment.invoice_number')
    subscription_purpose = serializers.SerializerMethodField()
    paid_date = serializers.SerializerMethodField()
    direct_debit = serializers.SerializerMethodField()

    class Meta:
        model = BaseTransaction
        fields = (
            'user', 'amount', 'transaction_type', 'is_paid', 'paid_date', 'title', 'payment', 'subscription_purpose', 'created_time',
            'direct_debit'
        )

    def get_direct_debit(self, obj):
        if hasattr(obj, 'subscription_peyman_transaction'):
            return obj.subscription_peyman_transaction.is_paid
        return False

    def get_title(self, obj):
        if hasattr(obj, 'subscription_transaction'):
            return obj.subscription_transaction.subscription.business.name

        if hasattr(obj, 'subscription_peyman_transaction'):
            return obj.subscription_peyman_transaction.subscription.business.name

        if hasattr(obj, 'target_transaction'):
            return obj.target_transaction.target.title

        return ''

    def get_subscription_purpose(self, obj):
        if obj.transaction_type == BaseTransaction.SUBSCRIPTION and getattr(obj.subscription_transaction,
                                                                            'subscription_purpose', None) is not None:
            return SubscriptionPurposeSerializer(obj.subscription_transaction.subscription_purpose).data

        if obj.transaction_type == BaseTransaction.DIRECT_DEBIT and getattr(obj.subscription_peyman_transaction,
                                                                            'subscription_purpose', None) is not None:
            return SubscriptionPurposeSerializer(obj.subscription_peyman_transaction.subscription_purpose).data

        return None

    def get_paid_date(self, obj):
        if hasattr(obj, 'subscription_transaction'):
            return obj.subscription_transaction.paid_date

        if hasattr(obj, 'subscription_peyman_transaction'):
            return obj.subscription_peyman_transaction.paid_date

        return None


class BaseTransactionPanelSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source='sub_trans.subscription.user.get_full_name')
    related_id = serializers.SerializerMethodField()
    tier = TierLightSerializer(source='sub_trans.subscription.tier')
    subscription_purpose = serializers.SerializerMethodField()
    created_time = serializers.DateTimeField(source='sub_trans.created_time')
    modified_time = serializers.DateTimeField(source='sub_trans.modified_time')
    status = serializers.IntegerField(source='sub_trans.status')

    class Meta:
        model = BaseTransaction
        fields = ('fullname', 'related_id', 'amount', 'tier', 'modified_time', 'created_time', 'status')

    def get_relation_id(self, obj):
        return obj.sub_trans.subscription.user.id

    def get_subscription_purpose(self, obj):
        if getattr(obj, 'sun_trans.subscription_purpose', None):
            return obj.sub_trans.subscription_purpose.title
        return None


class TargetTransactionCreateSerializer(serializers.ModelSerializer):
    transaction = BaseTransactionInlineSerializer(read_only=True)
    amount = serializers.IntegerField(required=False)

    class Meta:
        model = TargetTransaction
        fields = ('id', 'target', 'transaction', 'amount')

    def validate(self, attrs):
        if not attrs['target'].has_dynamic_amount:
            attrs['amount'] = attrs['target'].fixed_amount
        elif attrs['target'].has_dynamic_amount and not attrs['amount']:
            raise ValidationError(_("Amount could not be empty"))
        return attrs

    def create(self, validated_data):
        transaction = BaseTransaction.objects.create(
            user=validated_data['user'], amount=validated_data['amount'], transaction_type=BaseTransaction.TARGET
        )
        _ = Payment.objects.create(
            user=validated_data['user'], amount=validated_data['amount'], transaction=transaction
        )
        return super().create({'transaction': transaction, 'target': validated_data['target']})


class TargetTransactionListSerializer(serializers.ModelSerializer):
    fullname = serializers.SerializerMethodField()
    relation_id = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    target = TargetLightSerializer()
    class Meta:
        model = TargetTransaction
        fields = (
            'fullname',
            'relation_id',
            'target',
            'amount',
            'is_paid',
            'modified_time',
            'created_time',
        )

    def get_fullname(self, obj):
        return obj.transaction.user.get_full_name()

    def get_relation_id(self, obj):
        return obj.transaction.user.id

    def get_amount(self, obj):
        return obj.transaction.amount


class BaseTransactionLightSerializer(serializers.ModelSerializer):
    business = serializers.SerializerMethodField()
    user = UserLightSerializer()
    created_time = serializers.SerializerMethodField()
    paid_date = serializers.SerializerMethodField()
    tier = serializers.SerializerMethodField()
    is_first_donate = serializers.SerializerMethodField()

    class Meta:
        model = BaseTransaction
        fields = ('user', 'transaction_type', 'business', 'created_time', 'paid_date', 'tier', 'is_first_donate')

    def get_business(self, obj):
        return BusinessLightSerializer(obj.related.subscription.business).data

    def get_created_time(self, obj):
        return obj.related.created_time

    def get_paid_date(self, obj):
        return obj.related.paid_date

    def get_tier(self, obj):
        return TierLightSerializer(obj.related.subscription.tier).data

    def get_is_first_donate(self, obj):
        count = SubscriptionTransaction.objects.select_related('transaction')\
                   .filter(transaction__user=obj.user, is_paid=True).count()
        return count == 1
