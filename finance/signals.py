from django.db.models.signals import post_save
from django.dispatch import receiver

from finance.models import Payment
from subscription.models.transactions import BaseTransaction


@receiver(post_save, sender=Payment)
def enable_user_credentials(sender, instance, created, **kwargs):
    """
    When bank callback API received and payment status changed, this signal
    would run and should check if payment related to the any subscription change
    subscription status too
    """
    if not instance.status_changed():
        """Payment status is not changed or is revert to False"""
        return

    if instance.is_wallet_charge():
        """Payment has no transaction and may just is for account charge"""
        BaseTransaction.check_owed(instance.user)
    else:
        transaction = instance.transaction.related
        transaction.set_paid()
