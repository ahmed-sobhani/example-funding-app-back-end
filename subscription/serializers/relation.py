from django.contrib.auth import get_user_model
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from django.utils.translation import ugettext_lazy as _

from business.models import Business
from content.models import Comment
from subscription.models import Relation, Subscription
from subscription.models.transactions import SubscriptionTransaction, SubscriptionPeymanTransaction
from subscription.serializers.subscriptions import SubscriptionLightSerializer
from subscription.serializers.transactions import SubscriptionInlineTransactionSerializer, \
    SubscriptionInlinePeymanTransactionSerializer

User = get_user_model()


class RelationCreateSerializer(serializers.ModelSerializer):
    """Relation Create serializer just receive one following account and set
    relation between request.user and sent following user"""
    following = serializers.SlugRelatedField(slug_field='url_path', queryset=Business.objects.all())

    class Meta:
        model = Relation
        fields = ('following', 'follower')

    def validate(self, attrs):
        if Relation.objects.filter(following=attrs['following'], follower=attrs['follower']).exists():
            raise ValidationError(_("Relation exists"))
        return attrs


class FollowerListSerializer(serializers.ModelSerializer):
    follower = serializers.CharField(source='follower.get_full_name')
    id = serializers.IntegerField(source='follower.id')
    phone_number = serializers.IntegerField(source='follower.phone_number')
    total_paid = serializers.SerializerMethodField()
    subscriptions = serializers.SerializerMethodField()
    is_enable = serializers.SerializerMethodField()

    class Meta:
        model = Relation
        fields = (
            'id', 'follower', 'created_time', 'subscriptions', 'phone_number', 'total_paid', 'is_enable'
        )

    def get_total_paid(self, obj):
        total_paid = SubscriptionTransaction.objects.select_related('transaction', 'subscription').filter(
            transaction__user=obj.follower, subscription__business=obj.following, is_paid=True, status=10
        ).aggregate(total=Coalesce(Sum('transaction__amount'), 0))['total']
        return total_paid

    def get_subscriptions(self, obj):
        subscriptions = Subscription.objects.filter(user=obj.follower, business=obj.following, is_enable=True)
        return SubscriptionLightSerializer(subscriptions, many=True).data

    def get_is_enable(self, obj):
        return bool(self.get_subscriptions(obj))


class RelationDetailSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='get_full_name')
    avatar = serializers.ImageField(source='profile.avatar')
    subscriptions = serializers.SerializerMethodField()
    subscription_transactions = serializers.SerializerMethodField()
    report = serializers.SerializerMethodField()
    created_time = serializers.DateTimeField(source='date_joined')
    description = serializers.SerializerMethodField()
    subscription_peyman_transaction = serializers.SerializerMethodField()
    total_owed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'user', 'subscriptions', 'subscription_transactions', 'report',
            'avatar', 'created_time', 'description', 'phone_number', 'subscription_peyman_transaction',
            'total_owed',
        )

    @property
    def business(self):
        request = self.context.get('request')
        if not hasattr(self, '_business'):
            setattr(self, '_business', request.user.business if request is not None else None)
        return self._business

    def get_total_owed(self, obj):
        return SubscriptionTransaction.objects.filter(transaction__user=obj, status=SubscriptionTransaction.OWED)\
            .aggregate(total=Coalesce(Sum('transaction__amount'), 0))['total']

    def get_subscriptions(self, obj):
        subscriptions = Subscription.objects.filter(user=obj, business=self.business, is_enable=True)
        return SubscriptionLightSerializer(subscriptions, many=True).data

    def get_subscription_transactions(self, obj):
        subscription_transactions = SubscriptionTransaction.objects.filter(
            subscription__user=obj, subscription__business=self.business
        ).filter(Q(status__in=[5, 10]) | Q(status=10)).order_by('-created_time')
        # ).filter(Q(subscription__is_enable=True, status__in=[5, 10]) | Q(status=10))
        return SubscriptionInlineTransactionSerializer(subscription_transactions, many=True).data

    def get_subscription_peyman_transaction(self, obj):
        subscription_peyman_transaction = SubscriptionPeymanTransaction.objects.filter(
            subscription__user=obj, subscription__business=self.business
        ).filter(Q(status__in=[5, 10]) | Q(status=10)).order_by('-created_time')
        return SubscriptionInlinePeymanTransactionSerializer(subscription_peyman_transaction, many=True).data

    def get_report(self, obj):
        subscription_transactions = SubscriptionTransaction.objects.filter(
            subscription__user=obj, subscription__business=self.business, is_paid=True
        )
        subscription_peyman_transactions = SubscriptionPeymanTransaction.objects.filter(
            subscription__user=obj, subscription__business=self.business, is_paid=True
        )
        subscriptions = Subscription.objects.filter(user=obj, business=self.business, is_enable=True)
        comments = Comment.objects.filter(post__business=self.business, user=obj)
        data = {
            'total_paid': subscription_transactions.aggregate(t=Coalesce(Sum('transaction__amount'), 0))['t'] +
                          subscription_peyman_transactions.aggregate(t=Coalesce(Sum('transaction__amount'), 0))['t'],
            'total_comments': comments.count(),
            'subscription_duration': (timezone.now() - subscriptions.first().created_time).days if subscriptions.first() else 0,
            'platforms': []

        }
        return data

    def get_description(self, obj):
        try:
            business = Business.objects.get(url_path=self.context.get('slug'))
            return obj.followings.get(following=business).description
        except:
            return ''