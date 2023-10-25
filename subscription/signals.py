from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from finance.models import Payment
from subscription.models import Subscription, BaseTransaction, Relation
from subscription.models.transactions import SubscriptionTransaction, TargetTransaction, SMSPackageTransaction


@receiver(post_save, sender=Subscription)
def set_relation_for_the_subscriber(sender, instance, created, **kwargs):
    """
    When a subscription created for specific user, system will automatically
    create a relation between user and business as
    """

    if instance.status_changed and instance.is_enable:
        Relation.objects.get_or_create(follower=instance.user, following=instance.business)


@receiver(post_save, sender=Subscription)
def set_first_transaction(sender, instance, created, **kwargs):
    """When a subscription created for specific user, first transaction should
    be initiated here, if user has enough value in wallet set successful
    transaction else set not paid transaction, create payment and bundle them
    together and let user to see the payment info"""
    if not created:
        """Subscription is not created recently"""
        return

    transaction = BaseTransaction(user=instance.user, amount=instance.tier.amount)
    subscription = SubscriptionTransaction(
        subscription=instance, due_date=timezone.now(), subscription_purpose=instance.subscription_purpose
    )

    wallet = BaseTransaction.wallet(instance.user)
    if instance.tier.amount <= wallet and instance.sub_auto_pay:
        """User has enough value in wallet to settle the tier for this step"""
        transaction.transaction_type = BaseTransaction.SUBSCRIPTION
        subscription.is_paid = True
        subscription.paid_date = timezone.now()
        transaction.save()
        subscription.status = SubscriptionTransaction.PAID
        subscription.transaction = transaction
        subscription.save()
        instance.is_enable = True
        instance.save()
    else:
        """Wallet value is not enough, so user should charge wallet"""
        transaction.transaction_type = BaseTransaction.INSTANT
        transaction.save()
        subscription.is_paid = False
        subscription.status = SubscriptionTransaction.CREATED
        subscription.transaction = transaction
        payment = Payment(
            amount=instance.tier.amount, user=instance.user,
            transaction=transaction
        )
        subscription.save()
        payment.save()


@receiver(post_save, sender=SubscriptionTransaction)
def notify_user(sender, instance, created, **kwargs):
    """Decide what to do when a SubscriptionTransaction is creating or editing
    condition rules are following:
        - Transaction is created:
            - Transaction is paid: Send greeting message to the user
            - Transaction is not paid: Send alert message to the user
        - Transaction status is changed and current status is True:
            Send greeting message to the user"""

    if created:
        if instance.is_paid:
            """Send greeting message to the user"""
            pass
        else:
            """Send alert message to the user"""

    elif instance.status_changed() and instance.is_paid:
        """Send greeting message to the user"""
        pass


@receiver(pre_save, sender=TargetTransaction)
def check_if_target_is_enable(sender, instance, **kwargs):
    """Disable business target if has reached to the defined amount"""
    if instance.status_changed():
        current_amount = instance.total_transactions_amount(target=instance.target)
        if instance.target.total_target_amount and instance.target.total_target_amount <= current_amount:
            instance.target.is_enable = False
