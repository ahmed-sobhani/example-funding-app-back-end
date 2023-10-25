from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from business.models import Business, Tier, SubscriptionPurpose
from lib.common_model import BaseModel
from subscription.models.relation import Relation
from utils.time import get_jalali_day_of_month

User = get_user_model()


class Subscription(BaseModel):
    """Store all subscriptions of all users on this table + selected tier"""
    BANK_APPROACH = 5
    PEYMAN_DIRECT_DEBIT = 10
    SUB_TYPE = (
        (PEYMAN_DIRECT_DEBIT, _("peyman direct debit")),
        (BANK_APPROACH, _("bank approach")),
    )
    user = models.ForeignKey(User, related_name='subscriptions', verbose_name=_("user"))
    business = models.ForeignKey(Business, related_name='subscribers', verbose_name=_("business"))
    tier = models.ForeignKey(Tier, related_name='subscribers', verbose_name=_("tier"))
    subscription_purpose = models.ForeignKey(
        SubscriptionPurpose, related_name='subscriptions', verbose_name=_("purpose"), null=True, blank=True
    )
    jalali_due_day_of_month = models.SmallIntegerField(verbose_name=_("jalali due day of month"), blank=True)
    end_date = models.DateTimeField(verbose_name=_('end date'), null=True, blank=True)
    is_enable = models.BooleanField(verbose_name=_('is enable'), default=False)
    sub_type = models.PositiveSmallIntegerField(verbose_name=_("sub type"), choices=SUB_TYPE, default=BANK_APPROACH)
    sub_auto_pay = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Subscription")
        verbose_name_plural = _("Subscriptions")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._b_is_enable = self.is_enable

    def __str__(self):
        return str(self.user) + str(self.business)

    @property
    def is_active(self):
        """
        Check if user has paid the last transaction of this subscription or not
        subscriptions which has not payment for 2 month will be changed to
        disable but user cannot see provided contents from day 3 of first month
        :return: Boolean
        """
        transaction = self.transactions.filter(status=5, is_paid=False).order_by('created_time').last()
        if transaction is not None:
            passed_day = timezone.now() - transaction.created_time
            return passed_day.days < 4
        return True

    @property
    def status_changed(self):
        return self.is_enable != self._b_is_enable

    @property
    def relation(self):
        return Relation.objects.filter(follower=self.user, following=self.business).first()

    def save(self, *args, **kwargs):
        if not self.jalali_due_day_of_month:
            today = self.created_time if self.created_time is not None else timezone.localtime(timezone.now())
            self.jalali_due_day_of_month = get_jalali_day_of_month(today)
        return super().save(*args, **kwargs)
