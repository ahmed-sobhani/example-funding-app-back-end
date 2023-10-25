from django.contrib.auth import get_user_model
from django.test import TestCase

from business.models import Business, Tier
from subscription.models import Subscription, BaseTransaction
from subscription.models.transactions import SubscriptionTransaction

User = get_user_model()


class PaymentTestCase(TestCase):
    fixtures = ['fixtures/business.json', 'fixtures/user.json']

    def setUp(self):
        self.user = User.objects.first()
        self.business = Business.objects.first()
        self.tier = Tier.objects.first()
        self.subscription = Subscription.objects.create(user=self.user, business=self.business, tier=self.tier)

    def test_wallet_charge_identification(self):
        self.assertEqual(BaseTransaction.wallet(self.user), 0, "Wallet charge is not 0 at initial time")
        base_transaction = BaseTransaction.objects.create(user=self.user, amount=self.subscription.tier.amount, transaction_type=BaseTransaction.SUBSCRIPTION)
        subscription_transaction = SubscriptionTransaction.objects.create()

    def test_owed_charge(self):
        # TODO: For instant payment
        # TODO: For wallet charge
        pass
