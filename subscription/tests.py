from django.test import TestCase

from business.models import Business, Tier
from finance.models import Payment
from subscription.models import Subscription, Relation, BaseTransaction
from subscription.models.transactions import SubscriptionTransaction
from subscription.tasks import charge_subscription
from user.models import User


class SubscriptionTestCase(TestCase):
    fixtures = ['fixtures/business.json']

    def setUp(self):
        self.user = User.objects.first()
        self.business = Business.objects.first()
        self.tier = Tier.objects.first()
        self.subscription = Subscription.objects.create(user=self.user, business=self.business, tier=self.tier)

    def test_subscription_process(self):
        self.assertFalse(self.subscription.is_enable, 'Subscription should not be enabled by default')
        self.assertFalse(Relation.objects.filter(follower=self.subscription.user, following=self.subscription.business).exists(), 'Relations already exists')
        self.subscription.is_enable = True
        self.subscription.save()
        self.assertTrue(self.subscription.status_changed, "Subscription status_changed is not working")
        self.assertTrue(Relation.objects.filter(follower=self.subscription.user, following=self.subscription.business).exists(), 'Relations does not created after subscription')

    def test_periodic_charge(self):
        self.assertEqual(BaseTransaction.wallet(self.user), 0, "User wallet is not 0 at initial state")
        self.assertEqual(self.subscription.transactions.filter(is_paid=True).count(), 0, "More than 1 transaction did for subscription")
        transaction = BaseTransaction.objects.create(user=self.user, transaction_type=5, amount=self.tier.amount*6)
        payment = Payment.objects.create(user=transaction.user, amount=transaction.amount, transaction=transaction, is_paid=True)
        self.assertTrue(payment.is_paid, "Invoice is not paid")
        self.assertEqual(BaseTransaction.wallet(self.user), self.tier.amount*6, "Wallet not charged yet")
        self.subscription.is_enable = True
        self.subscription.save()
        result, message = charge_subscription(self.subscription.id)
        self.assertTrue(result, "Subscription charge was not successful, error: {}".format(message))
        self.assertEqual(self.subscription.transactions.filter(is_paid=True).count(), 1, "More than 1 transaction did for subscription")
        self.assertEqual(BaseTransaction.wallet(self.user), self.tier.amount*5, "User Charge wallet is not working in right way")
        subscription_transaction = self.subscription.transactions.first()
        self.assertEqual(self.subscription.subscription_purpose, subscription_transaction.subscription_purpose, "Purpose is not set")

    def test_wallet_charge_actions(self):
        self.assertEqual(BaseTransaction.wallet(self.user), 0, 'User wallet is not empty at initial point')
        self.subscription.is_enable = True
        self.subscription.save()
        self.assertEqual(self.subscription.transactions.count(), 1, 'More than 1 transaction did to current subscription')
        result, message = charge_subscription(self.subscription.id)
        subscription_transaction = self.subscription.transactions.last()
        self.assertEqual(subscription_transaction.status, SubscriptionTransaction.OWED, "Created transaction status is not correct")
        self.assertFalse(subscription_transaction.is_paid, "Created transaction is paid !!")
        transaction = BaseTransaction.objects.create(user=self.user, transaction_type=5, amount=self.tier.amount * 6)
        payment = Payment.objects.create(user=transaction.user, amount=transaction.amount, transaction=transaction, is_paid=False)
        payment.is_paid = True
        payment.save()
        subscription_transaction = self.subscription.transactions.last()
        self.assertTrue(payment.is_paid, 'Invoice is not paid')
        self.assertEqual(BaseTransaction.wallet(self.user), self.tier.amount * 5, 'User wallet amount is not correct')
        self.assertEqual(subscription_transaction.status, SubscriptionTransaction.PAID, "Owed transaction status not changed")
        self.assertTrue(subscription_transaction.is_paid, "Created transaction is paid !!")
