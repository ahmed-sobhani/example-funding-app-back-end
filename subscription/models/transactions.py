from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Sum, Q, Count
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from business.models import Target, SubscriptionPurpose, SMSPackage
from lib.common_model import BaseModel
from .subscription import Subscription

User = get_user_model()


class BaseTransaction(BaseModel):
    """Base Transaction handler saves all type of transactions here and manage
    other credentials through related models, all types of transactions on the
    system should have OneToOne relation to this model"""
    WALLET_CHARGE = 5
    TARGET = 10
    SUBSCRIPTION = 15
    INSTANT = 20
    DIRECT_DEBIT = 25
    SMS_PACKAGE = 30
    FOLLOWER_WALLET_CHARGE = 35
    TYPE_CHOICES = (
        (WALLET_CHARGE, _("Wallet charge")),
        (TARGET, _("Target")),
        (SUBSCRIPTION, _("Subscription")),
        (INSTANT, _("Instant")),
        (DIRECT_DEBIT, _("direct debit")),
        (SMS_PACKAGE, _("SMS package")),
        (FOLLOWER_WALLET_CHARGE, _("Follower wallet charge")),
    )

    user = models.ForeignKey(User, related_name='transactions', verbose_name=_("user"))
    amount = models.IntegerField(verbose_name=_("amount"))
    transaction_type = models.IntegerField(verbose_name=_("transaction type"), choices=TYPE_CHOICES, default=SUBSCRIPTION)

    class Meta:
        verbose_name = _("BaseTransaction")
        verbose_name_plural = _("BaseTransactions")

    def __str__(self):
        return '{}({}): {}'.format(self.user, self.get_transaction_type_display(), self.amount)

    @property
    def related_key(self):
        handlers_map = {
            5: 'payment', 10: 'target_transaction',
            15: 'subscription_transaction', 20: 'subscription_transaction',
            25: 'subscription_peyman_transaction',
            35: 'follower_wallet_charge_transaction'
        }
        return handlers_map[self.transaction_type]

    @property
    def related(self):
        return getattr(self, self.related_key)

    @property
    def is_paid(self):
        if self.related.is_paid:
            return True
        return False

    @property
    def title(self):
        return getattr(self.related, 'title', '')

    @classmethod
    def wallet(cls, user):
        """Get user and calculate wallet value of user by subtracting bank
        payments from other transactions and return inter as response"""
        user_transactions = cls.objects.filter(user=user)
        positive_amount = user_transactions.filter(
            Q(transaction_type=cls.WALLET_CHARGE, payment__is_paid=True) |
            Q(transaction_type=cls.FOLLOWER_WALLET_CHARGE, payment__is_paid=True) |
            Q(transaction_type=cls.SUBSCRIPTION, payment__is_paid=True)
        ).aggregate(total=Coalesce(Sum('amount'), 0))
        negative_amount = user_transactions.filter(
            # Q(transaction_type=cls.TARGET, target_transaction__is_paid=True) |
            Q(transaction_type=cls.SUBSCRIPTION, subscription_transaction__is_paid=True) |
            Q(transaction_type=cls.SMS_PACKAGE, sms_package_transaction__is_paid=True)
        ).aggregate(total=Coalesce(Sum('amount'), 0))
        balance = positive_amount['total'] - negative_amount['total']
        return balance if balance > 0 else 0

    @classmethod
    def check_owed(cls, user):
        """
        Check user user has owed transaction or not and flagged as paid if
        wallet has enough charge
        :param user: user instance
        :return: None
        """
        owed_transactions = SubscriptionTransaction.objects.select_related('subscription').filter(
            subscription__user=user, subscription__is_enable=True, status=SubscriptionTransaction.OWED
        )
        for owed in owed_transactions:
            if cls.wallet(user) >= owed.transaction.amount:
                owed.is_paid = True
                owed.status = SubscriptionTransaction.PAID
                owed.paid_date = timezone.now()
                owed.save()
        return


class FollowerWalletCharge(BaseModel):
    transaction = models.OneToOneField(BaseTransaction, verbose_name=_("transaction"),
                                       related_name='follower_wallet_charge_transaction')
    operator = models.ForeignKey(User, verbose_name=_("operator"), related_name='follower_wallet_charge_transaction')
    follower = models.ForeignKey(User, verbose_name=_("follower"), related_name='operator_wallet_charge_transaction')
    is_paid = models.BooleanField(default=False, verbose_name=_("is paid"))

    class Meta:
        verbose_name = _("Follower wallet transaction")
        verbose_name_plural = _("Follower wallet transactions")

    def __str__(self):
        return "{}: {}".format(self.operator, self.follower)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._b_is_paid = self.is_paid

    def set_paid(self):
        """Set transaction is_paid =>> True"""
        if not self.is_paid:
            self.is_paid = True
            self.save()


class SMSPackageTransaction(BaseModel):
    transaction = models.OneToOneField(BaseTransaction, verbose_name=_("transaction"), related_name='sms_package_transaction')
    sms_package = models.ForeignKey(SMSPackage, related_name='transactions', verbose_name=_('sms package'))
    is_paid = models.BooleanField(default=False, verbose_name=_("is paid"))

    class Meta:
        verbose_name = _("SMS Transaction")
        verbose_name_plural = _("SMS Transactions")

    def __str__(self):
        return "{}: {}".format(self.sms_package.count, self.sms_package.amount)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._b_is_paid = self.is_paid

    def set_paid(self):
        """Set transaction is_paid =>> True"""
        if not self.is_paid:
            self.is_paid = True
            self.save()


class TargetTransaction(BaseModel):
    """Save all transactions for each target defined in business panel"""
    transaction = models.OneToOneField(BaseTransaction, verbose_name=_("transaction"), related_name='target_transaction')
    target = models.ForeignKey(Target, related_name='transactions', verbose_name=_('target'))
    is_paid = models.BooleanField(default=False, verbose_name=_("is paid"))

    class Meta:
        verbose_name = _("TargetTransaction")
        verbose_name_plural = _("TargetTransactions")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._b_is_paid = self.is_paid

    def __str__(self):
        return "{}: {}".format(self.target.business.name, self.transaction.amount)

    @property
    def title(self):
        return "{} - {}".format(self.target.business.name, self.target.title)

    def status_changed(self):
        return self._b_is_paid != self.is_paid

    def set_paid(self):
        """Set transaction is_paid =>> True"""
        if not self.is_paid:
            self.is_paid = True
            self.save()

    @classmethod
    def total_transactions_amount(cls, business=None, target=None):
        queryset = cls.objects.filter(is_paid=True)

        if target is not None:
            queryset = queryset.filter(target=target)

        if business is not None:
            queryset = queryset.filter(target__business=business)

        agg = queryset.aggregate(t=Coalesce(Sum('transaction__amount'), 0))
        return agg['t']

    @classmethod
    def total_transactions_count(cls, business=None, target=None, distinct=False):
        queryset = cls.objects.filter(is_paid=True)
        if target is not None:
            queryset = queryset.filter(target=target)

        if business is not None:
            queryset = queryset.filter(target__business=business)

        if distinct is True:
            agg = queryset.values('transaction__user').distinct().aggregate(
                t=Coalesce(Count('transaction__amount'), 0))
        else:
            agg = queryset.aggregate(t=Coalesce(Count('transaction__amount'), 0))

        return agg['t']

    @classmethod
    def total_transactions_users(cls, business=None):
        queryset = cls.objects.filter(is_paid=True)
        if business is not None:
            queryset = queryset.filter(target__business=business)
        return queryset.distinct('transaction__user').count()


class SubscriptionTransaction(BaseModel):
    """Save all subscription related transactions here. For each subscription
    we store due_date and paid_date to not how to react financial terms"""
    CREATED = 0
    OWED = 5
    PAID = 10
    STATUS_CHOICES = (
        (CREATED, _("Created")),
        (OWED, _("Owed")),
        (PAID, _("Paid")),
    )
    transaction = models.OneToOneField(
        BaseTransaction, verbose_name=_("transaction"), related_name='subscription_transaction'
    )
    subscription = models.ForeignKey(Subscription, verbose_name=_('subscription'), related_name='transactions')
    subscription_purpose = models.ForeignKey(
        SubscriptionPurpose, related_name='transactions', verbose_name=_("purpose"), null=True, blank=True
    )
    due_date = models.DateTimeField(verbose_name=_("due date"))
    is_paid = models.BooleanField(default=True, verbose_name=_("is paid"))
    paid_date = models.DateTimeField(null=True, blank=True)
    status = models.PositiveSmallIntegerField(verbose_name=_("status"), choices=STATUS_CHOICES, default=CREATED)

    class Meta:
        verbose_name = _("SubscriptionTransaction")
        verbose_name_plural = _("SubscriptionTransactions")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._b_is_paid = self.is_paid

    def __str__(self):
        return "{}: {}".format(self.subscription.business.name, self.transaction.amount)

    @property
    def title(self):
        return "{} - {}".format(self.subscription.tier.title, self.subscription.business.name)

    def status_changed(self):
        """Check weather status is changed during actions or not"""
        return self._b_is_paid != self.is_paid

    def set_paid(self):
        """Set transaction is_paid =>> True and status  =>> PAID"""
        if not self.is_paid:
            self.is_paid = True
            self.status = SubscriptionTransaction.PAID
            self.paid_date = timezone.now()
            self.save()
            self.subscription.is_enable = True
            self.subscription.save()


class SubscriptionPeymanTransaction(BaseModel):
    CREATED = 0
    PAID = 10
    FAILED = 20
    STATUS_CHOICES = (
        (CREATED, _("created")),
        (PAID, _("paid")),
        (FAILED, _("failed")),
    )
    transaction = models.OneToOneField(
        BaseTransaction, verbose_name=_("transaction"), related_name='subscription_peyman_transaction')
    subscription = models.ForeignKey(Subscription, verbose_name=_('subscription'), related_name='peyman_transactions')
    peyman = models.ForeignKey(
        'peyman.Peyman', verbose_name=_("peyman"), related_name='subscription_transactions', on_delete=models.CASCADE
    )
    peyman_transaction = models.OneToOneField(
        'peyman.PeymanTransaction', verbose_name=_("peyman transaction"), related_name='subscription_peyman',
        on_delete=models.CASCADE, null=True, blank=True
    )
    subscription_purpose = models.ForeignKey(
        SubscriptionPurpose, related_name='peyman_transactions', verbose_name=_("purpose"), null=True, blank=True
    )
    is_paid = models.BooleanField(default=False, verbose_name=_("is paid"))
    status = models.PositiveSmallIntegerField(verbose_name=_("status"), choices=STATUS_CHOICES, default=CREATED)
    paid_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(verbose_name=_("due date"), blank=True, null=True)

    class Meta:
        verbose_name = _("SubscriptionPeymanTransaction")
        verbose_name_plural = _("SubscriptionsPeymansTransactions")

    def __str__(self):
        return "{}: {}".format(self.subscription.business.name, self.transaction.amount)

    def set_paid(self):
        """Set transaction is_paid =>> True and status  =>> PAID"""
        if not self.is_paid:
            self.is_paid = True
            self.status = SubscriptionTransaction.PAID
            self.paid_date = timezone.now()
            self.save()
            self.subscription.is_enable = True
            self.subscription.save()
