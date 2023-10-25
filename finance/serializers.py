from django.urls import reverse
from rest_framework import serializers

from finance.models import Payment, Gateway
from subscription.models import BaseTransaction
from user.serializers import UserLightSerializer


class PaymentInlineSerializer(serializers.ModelSerializer):
    """Payment inline serializer will serializer just data for payment and
    gateway models not other related and is safe to be used inside another
    serializers (except gateway), because will not cause recursion"""
    gateways = serializers.SerializerMethodField()
    gateway = serializers.SlugRelatedField(
        slug_field='gateway_code', read_only=True
    )

    class Meta:
        model = Payment
        fields = (
            'invoice_number', 'amount', 'gateway', 'is_paid', 'gateways'
        )
        extra_kwargs = {'is_paid': {'read_only': True}}

    def get_gateways(self, obj):
        gateways = list()
        if obj.is_paid:
            return gateways
        for gateway in Gateway.objects.filter(is_enable=True):
            gateways.append(
                {
                    'title': gateway.title,
                    'code': gateway.gateway_code,
                    'url': reverse('payment', args=[obj.invoice_number,
                                                    gateway.gateway_code])
                }
            )
        return gateways


class PaymentLightSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment
        fields = (
            'invoice_number', 'amount', 'gateway', 'is_paid',
            'transaction', 'user'
        )
        extra_kwargs = {'is_paid': {'read_only': True}, 'transaction': {'read_only': True},
                        'invoice_number': {'read_only': True}}


class PaymentSerializer(serializers.ModelSerializer):
    """Payment complete serializer which will serializer transaction data too"""
    gateways = serializers.SerializerMethodField()
    gateway = serializers.SlugRelatedField(
        slug_field='gateway_code', read_only=True
    )
    transaction = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            'invoice_number', 'amount', 'gateway', 'is_paid', 'gateways',
            'transaction', 'created_time'
        )
        extra_kwargs = {'is_paid': {'read_only': True}}

    def get_gateways(self, obj):
        gateways = list()
        if obj.is_paid:
            return gateways
        for gateway in Gateway.objects.filter(is_enable=True):
            gateways.append(
                {
                    'title': gateway.title,
                    'code': gateway.gateway_code,
                    'url': reverse(
                        'payment', args=[obj.invoice_number, gateway.gateway_code]
                    )
                }
            )
        return gateways

    def get_transaction(self, obj):
        if obj.transaction.transaction_type == BaseTransaction.INSTANT:
            from subscription.serializers.transactions import \
                SubscriptionInlineTransactionSerializer
            serializer = SubscriptionInlineTransactionSerializer(
                obj.transaction.subscription_transaction, context=self.context
            )
            return serializer.data
        return {}


class WalletChargeSerializer(serializers.ModelSerializer):
    """When user request to charge wallet, will create base transaction and
    payment instance and then return payment data to continue next bank steps"""
    payment = PaymentInlineSerializer(read_only=True)
    user = UserLightSerializer(read_only=True)

    class Meta:
        model = BaseTransaction
        fields = ('user', 'amount', 'transaction_type', 'title', 'payment')

    def create(self, validated_data):
        validated_data['transaction_type'] = BaseTransaction.WALLET_CHARGE
        instance = super().create(validated_data)
        Payment.objects.create(
            user=validated_data['user'],
            amount=validated_data['amount'],
            transaction=instance
        )
        return instance
