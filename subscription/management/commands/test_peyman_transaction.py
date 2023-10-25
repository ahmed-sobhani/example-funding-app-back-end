from django.core.management.base import BaseCommand
from subscription.models import Subscription
from subscription.models.transactions import SubscriptionPeymanTransaction, BaseTransaction
from peyman.models import PeymanTransaction
from peyman.utils import peyman_direct_debit

from django.conf import settings
from django.utils import timezone


class Command(BaseCommand):
    def get_specific_date_direct_debit_subscription_charges(self, sid=None):
        if sid == "" or sid is None:
            return
        print("* START FIRST TASK *")
        subscription = Subscription.objects.get(id=int(sid))
        print("* subscription info *")
        print("subscription: ", subscription)
        print(subscription.user)
        print(subscription.business)
        print(subscription.tier)
        print(subscription.subscription_purpose)
        print(subscription.is_enable)
        print(subscription.sub_type)
        print("* subscription info *")

        date = timezone.now()
        print("date: ", date)
        last_transaction = subscription.peyman_transactions.last()

        print("* last transaction info *")
        print("last_transaction: ", last_transaction)
        print(last_transaction.transaction)
        print(last_transaction.peyman)
        print(last_transaction.peyman_transaction)
        print(last_transaction.is_paid)
        print(last_transaction.status)
        print(last_transaction.paid_date)
        print("* last transaction info *")

        if last_transaction is not None and (last_transaction.created_time.date() == date.date()) and \
                (last_transaction.status == SubscriptionPeymanTransaction.PAID):
            print("* transaction paid *")
        self.direct_debit_charge_subscription(subscription.id)

    def direct_debit_charge_subscription(self, sid, date=None):
        print("* START SECOND TASK *")
        subscription = Subscription.objects.filter(pk=sid, is_enable=True).first()
        print('subscription: ', subscription)
        if subscription is None:
            return False, "Subscription does not exists and/or is not enable"

        if date is None:
            date = timezone.now()
        print("date: ", date)

        peyman = subscription.peyman_transactions.first().peyman
        print("* peyman info *")
        print('peyman: ', peyman)
        print(peyman.peyman_code)
        print(peyman.peyman_id)
        print(peyman.bank_code)
        print(peyman.start_date)
        print(peyman.expiration_date)
        print(peyman.status)
        print(peyman.user)
        print(peyman.trace_id)
        print("* peyman info *")

        # print('have_succeed_transaction_in_month: ', peyman.have_succeed_transaction_in_month())
        # if not peyman.have_succeed_transaction_in_month():
        client_data = peyman.extra_data
        print('client data: ', client_data)
        peyman_trans_obj = peyman_direct_debit(
            peyman_id=peyman.peyman_id, amount=subscription.tier.amount * 10, phone_number=peyman.user.phone_number,
            **client_data
        )
        if isinstance(peyman_trans_obj, PeymanTransaction):
            print('* PAID *')
            status = SubscriptionPeymanTransaction.PAID
            paid_date = timezone.now()
            is_paid = True
        else:
            print('* CREATED *')
            status = SubscriptionPeymanTransaction.CREATED
            paid_date = None
            is_paid = False

        base_transaction = BaseTransaction.objects.create(
            user=subscription.user, amount=subscription.tier.amount,
            transaction_type=BaseTransaction.DIRECT_DEBIT
        )
        subscription_transaction = SubscriptionPeymanTransaction(
            transaction=base_transaction, subscription=subscription, peyman=peyman,
            due_date=date, status=status, is_paid=is_paid,
        )
        if paid_date is not None:
            subscription_transaction.paid_date = paid_date
            subscription_transaction.peyman_transaction = peyman_trans_obj
        if subscription.subscription_purpose is not None:
            subscription_transaction.subscription_purpose = subscription.subscription_purpose
        subscription_transaction.save()

        if subscription_transaction.is_paid:
            print("greeting")
        else:
            number_of_failed = settings.NUMBER_OF_PEYMAN_TRANSACTION_FAILED_FOR_SMS
            if peyman.number_of_failed_transaction_in_month() in number_of_failed:
                # TODO: must be changed with proper SMS pattern
                print("due_date_notify")
        return True, "Task done without error"

    def handle(self, *args, **kwargs):
        print("test start")
        sid = "7449"
        self.get_specific_date_direct_debit_subscription_charges(sid=sid)
