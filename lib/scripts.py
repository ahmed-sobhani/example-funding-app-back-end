from django.db.models import Count
from django.utils import timezone
from django.db.models import Case, When, Count, Sum, Q, F
from django.db.models.functions import Coalesce
from datetime import timedelta
from utils.time import get_start_day_of_month
from business.models import Business
from subscription.models.transactions import SubscriptionTransaction, SubscriptionPeymanTransaction
from subscription.tasks import send_business_income_notification


def test_transactions(slug='borhan'):
    print('************ DATES **************')
    date = timezone.localtime(timezone.now())
    print('date: ', date)
    last_day_date = date - timedelta(hours=24)
    print('last_day_date: ', last_day_date)
    start_day_of_month = get_start_day_of_month(timezone.now())
    print('start_day_of_month: ', start_day_of_month)

    print('************ TRANSACTIONS **************')
    business = Business.objects.get(url_path=slug)
    print('business: ', business)
    # for business in all_business:
    #     if business.user.phone_number is None:
    #         continue

    all_paid_transactions = SubscriptionTransaction.objects.filter(
        subscription__business=business,
        status=SubscriptionTransaction.PAID,
    )
    print('all_paid_transactions: ', all_paid_transactions)

    all_paid_direct_debit_transactions = SubscriptionPeymanTransaction.objects.filter(
        subscription__business=business,
        status=SubscriptionPeymanTransaction.PAID,
    )
    print('all_paid_direct_debit_transactions: ', all_paid_direct_debit_transactions)

    all_last_day_paid_transactions = all_paid_transactions.filter(
        paid_date__gt=last_day_date,
    )
    print('all_last_day_paid_transactions: ', all_last_day_paid_transactions)

    all_last_day_paid_direct_debit_transactions = all_paid_direct_debit_transactions.filter(
        paid_date__gt=last_day_date,
    )
    print('all_last_day_paid_direct_debit_transactions: ', all_last_day_paid_direct_debit_transactions)

    last_day_payment = all_last_day_paid_transactions.aggregate(t=Coalesce(Sum('transaction__amount'), 0))['t'] + \
                       all_last_day_paid_direct_debit_transactions.aggregate(t=Coalesce(Sum('transaction__amount'),
                                                                                            0))['t']
    print('last_day_payment: ', last_day_payment)

    # if last_day_payment == 0:
    #     continue

    last_month_payment = all_paid_transactions.filter(
        paid_date__gte=start_day_of_month,
    ).aggregate(t=Coalesce(Sum('transaction__amount'), 0))['t'] + \
                         all_paid_direct_debit_transactions.filter(
                             paid_date__gte=start_day_of_month,
                         ).aggregate(t=Coalesce(Sum('transaction__amount'), 0))['t']
    print('last_month_payment: ', last_month_payment)

    last_day_payment_count = all_last_day_paid_transactions.aggregate(t=Coalesce(Count('id'), 0))['t'] + \
                             all_last_day_paid_direct_debit_transactions.aggregate(t=Coalesce(Count('id'), 0))['t']
    print('last_day_payment_count: ', last_day_payment_count)

    # print(last_day_payment_count, last_day_payment, last_month_payment, business.user.phone_number)
    send_business_income_notification.delay(
        last_day_payment_count, last_day_payment, last_month_payment, 989185790596)