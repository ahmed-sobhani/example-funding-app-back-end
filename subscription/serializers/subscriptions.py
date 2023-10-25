from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from django.utils.translation import ugettext_lazy as _
from django.core import validators

from business.serializers import BusinessLightSerializer, TierLightSerializer

from peyman.utils import call_peyman_service
from subscription.models import Subscription, BaseTransaction
from subscription.models.transactions import SubscriptionPeymanTransaction, SubscriptionTransaction

import datetime

from django.contrib.auth import get_user_model, authenticate

User = get_user_model()


class SubscriptionLightSerializer(serializers.ModelSerializer):
    """
    Light data serializer for Subscription model
    """
    username = serializers.CharField(source='user.get_full_name')
    business = serializers.CharField(source='business.name')
    avatar = serializers.ImageField(source='business.avatar')
    url_path = serializers.CharField(source='business.url_path')
    tier = TierLightSerializer()
    subscription_purpose = serializers.SerializerMethodField()
    paid_date = serializers.DateTimeField(read_only=True)
    is_first_donate = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = (
            'id', 'username', 'business', 'url_path', 'url_path', 'tier',
            'subscription_purpose', 'created_time', 'paid_date', 'avatar', 'is_first_donate', 'sub_type'
        )

    def get_subscription_purpose(self, obj):
        if getattr(obj, 'subscription_purpose', None):
            return obj.subscription_purpose.title
        return None

    def get_is_first_donate(self, obj):
        count = SubscriptionTransaction.objects.select_related('transaction')\
                   .filter(transaction__user=obj.user, is_paid=True).count()
        return count == 1


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    """Serializer which used when a user request to subscribe in specific
    tier of one content provider, business and tier will given from request
    data and subscriber will be passed by request user"""
    transaction = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ('id', 'business', 'tier', 'transaction', 'subscription_purpose')

    def validate_tier(self, attr):
        if attr.limit and attr.subscribers.count() >= attr.limit:
            raise ValidationError(_("This tier has reached to maximum subscribers limit"))
        return attr

    def validate_subscription_purpose(self, attr):
        """Check selected purpose is enabled by content provider or not"""
        if not attr.enable:
            raise ValidationError(_("Subscription purpose is not active now"))
        return attr

    def validate(self, attrs):
        """Check correctness of business and tier"""
        if attrs['business'] != attrs['tier'].business:
            raise ValidationError(_("Selected tier is not available for selected business"))
        if 'subscription_purpose' in attrs:
            if attrs['subscription_purpose'].business != attrs['business']:
                raise ValidationError(_("Select purpose is not related to the selected business"))
            if Subscription.objects.filter(
                user=self.context["request"].user,  tier=attrs['tier'], subscription_purpose=attrs['subscription_purpose'], is_enable=True
            ).exists():
                raise ValidationError(_("Previously subscribed to this tier for this exact purpose"))
        elif 'subscription_purpose' not in attrs:
            if attrs['business'].purposes.filter(enable=True).exists():
                raise ValidationError(_("You must select one subscription purpose"))
            elif Subscription.objects.filter(user=self.context["request"].user,  tier=attrs['tier'], is_enable=True).exists():
                raise ValidationError(_("Previously subscribed to this tier"))
        return attrs

    def get_transaction(self, obj):
        transaction = obj.transactions.first()
        from subscription.serializers.transactions import \
            SubscriptionTransactionSerializer
        serializer = SubscriptionTransactionSerializer(
            transaction, context=self.context
        )
        return serializer.data

    def create(self, validated_data):
        instance = super().create(validated_data)

        # create peyman and related instances
        peyman_data = self.context['request'].data.pop("peyman_data", None)
        if peyman_data is not None:

            now = datetime.datetime.now()
            if now.hour == 23 and now.minute >= 45 or now.hour == 0 and now.minute < 30:
                raise ValidationError("Please try again after 00:30")

            national_code = self.context['request'].user.profile.national_code
            peyman_data['national_code'] = national_code if national_code is not None else peyman_data['national_code']
            peyman_obj, boom_url = call_peyman_service(
                phone_number=self.context['request'].user.phone_number, **peyman_data
            )
            if boom_url is None:
                err = peyman_obj.error
                raise ValidationError(err)
            base_transaction = BaseTransaction.objects.create(
                user=self.context['request'].user,
                amount=instance.tier.amount,
                transaction_type=BaseTransaction.DIRECT_DEBIT
            )
            SubscriptionPeymanTransaction.objects.create(
                transaction=base_transaction, subscription=instance, peyman=peyman_obj, due_date=timezone.now()
            )
            self.context['boom_url'] = boom_url

        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        ret['boom_url'] = self.context.get('boom_url')
        return ret


class SubscriptionListSerializer(serializers.ModelSerializer):
    """Serialize and use subscriptions to the different businesses"""
    business = BusinessLightSerializer()
    tier = TierLightSerializer()
    subscription_purpose = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ('id', 'business', 'tier', 'created_time', 'subscription_purpose', 'is_enable', 'sub_type')

    def get_subscription_purpose(self, obj):
        if obj.subscription_purpose is not None:
            return obj.subscription_purpose.title
        return '-'


class SubscriptionDetailSerializer(serializers.ModelSerializer):
    """Serialize and use subscriptions to the different businesses"""
    business = BusinessLightSerializer()
    tier = TierLightSerializer()
    message = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ('business', 'tier', 'created_time', 'is_enable', 'message')

    def get_message(self, obj):
        message = obj.business.messages.first()
        if message is not None:
            return message.description
        return ''


class SubscriberList(serializers.ModelSerializer):
    """Readonly serializer which calculate and aggregate subscriber data for
    each business and return to be shown in table"""
    fullname = serializers.CharField(source='user.get_full_name')
    tier = serializers.CharField(source='tier.title')
    total_paid_amount = serializers.SerializerMethodField(source='get_total')
    subscription_date = serializers.DateTimeField(source='created_time')
    last_paid_date = serializers.SerializerMethodField(source='get_last_paid')

    class Meta:
        model = Subscription
        fields = (
            'fullname', 'tier', 'total_paid_amount', 'subscription_date', 'last_paid_date', 'is_enable', 'is_active'
        )

    def get_total_paid_amount(self, obj):
        """aggregate total paid amount of current user on this tier"""
        all_transactions = obj.transactions.filter(is_paid=True).aggregate(
            total=Coalesce(Sum('transaction__amount'), 0)
        )
        return all_transactions['total']

    def get_last_paid_date(self, obj):
        """find last payment date of current user on this tier"""
        last_paid = obj.transactions.filter(is_paid=True).last()
        if last_paid:
            # TODO: Checkout to paid_date later
            # return last_paid.paid_date
            return last_paid.modified_time
        return None


class RegisterUserWithTierSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True,
                                         validators=[validators.RegexValidator(regex=r'^989[0-3,9]\d{8}$')])
    fullname = serializers.CharField(required=True)
    subscription = SubscriptionCreateSerializer()

    def create(self, validated_data):
        with transaction.atomic():
            try:
                user = User.objects.create_user(phone_number=validated_data.get("phone_number"))
            except:
                raise ValidationError(_("user already exist."))

            fullname_strip = str(validated_data.get("fullname")).split()
            user.first_name = fullname_strip[0]
            if len(fullname_strip) > 1:
                user.last_name = ' '.join(fullname_strip[1:])
            user.save()
            user.profile.verified = True
            user.profile.save()

            self.context["request"].user = user
            validated_data._mutable = True
            validated_data.pop("phone_number")
            validated_data.pop("fullname")
            sub = SubscriptionCreateSerializer(data=validated_data, context=self.context)
            if sub.is_valid():
                return sub.save(user=user)
            raise ValidationError(_("something went wrong."))
