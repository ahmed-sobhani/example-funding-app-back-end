import sys
import logging
import datetime
from datetime import timedelta
from celery import shared_task
from celery.schedules import crontab
from celery.task import periodic_task
from django.contrib.auth import get_user_model
from django.db import transaction
from django.template import loader
from django.utils import timezone
from django.conf import settings
from django.db.models import Case, When, Count, Sum, Q, F
from django.db.models.functions import Coalesce

from finance.models import Payment
from peyman.models import PeymanTransaction
from peyman.utils import peyman_direct_debit
from subscription.models import Subscription
from business.models import Business

from subscription.models.transactions import SubscriptionTransaction, BaseTransaction, SubscriptionPeymanTransaction

from utils.kavenegar import send_template_message
from utils.time import get_start_day_of_month

from utils.links import make_short
from utils.notifications import notify_user
from utils.time import get_related_jalali_day_of_month, get_related_next_jalali_day_of_month

User = get_user_model()

logger = logging.getLogger(__file__)


@shared_task(name='Get last 24-h subscription transactions')
def get_last_day_subscription_transaction():
    date = timezone.localtime(timezone.now())
    last_day_date = date - timedelta(hours=24)
    start_day_of_month = get_start_day_of_month(timezone.now())

    all_business = Business.objects.all()

    for business in all_business:
        if business.user.phone_number is None:
            continue

        all_paid_transactions = SubscriptionTransaction.objects.filter(
            subscription__business=business,
            status=SubscriptionTransaction.PAID,
        )
        all_paid_direct_debit_transactions = SubscriptionPeymanTransaction.objects.filter(
            subscription__business=business,
            status=SubscriptionPeymanTransaction.PAID,
        )

        all_last_day_paid_transactions = all_paid_transactions.filter(
            paid_date__gt=last_day_date,
        )
        all_last_day_paid_direct_debit_transactions = all_paid_direct_debit_transactions.filter(
            paid_date__gt=last_day_date,
        )

        last_day_payment = all_last_day_paid_transactions.aggregate(t=Coalesce(Sum('transaction__amount'), 0))['t'] + \
                           all_last_day_paid_direct_debit_transactions.aggregate(t=Coalesce(Sum('transaction__amount'),
                                                                                            0))['t']

        if last_day_payment == 0:
            continue

        last_month_payment = all_paid_transactions.filter(
            paid_date__gte=start_day_of_month,
        ).aggregate(t=Coalesce(Sum('transaction__amount'), 0))['t'] + \
                             all_paid_direct_debit_transactions.filter(
                                 paid_date__gte=start_day_of_month,
                             ).aggregate(t=Coalesce(Sum('transaction__amount'), 0))['t']

        last_day_payment_count = all_last_day_paid_transactions.aggregate(t=Coalesce(Count('id'), 0))['t'] + \
                                 all_last_day_paid_direct_debit_transactions.aggregate(t=Coalesce(Count('id'), 0))['t']

        send_business_income_notification.delay(
                        last_day_payment_count, f'{last_day_payment:,}', f'{last_month_payment:,}',
            business.user.phone_number)


# @shared_task(name='Get last 24-h subscription transactions')
# def get_last_day_subscription_transaction2():
#     """
#      - calculate the business income (last day, this month)
#      - loop over last_day_income and pass them to the send_business_income_notification
#     """
#     date = timezone.localtime(timezone.now())
#     last_day_date = date - timedelta(hours=24)
#     first_month_date = get_start_day_of_month()
#     # logger_1
#     logger.info('******** Send income SMS <get_last_day_subscription_transaction  ***************')
#     logger.info('date= {0},  first_month_date= {1}'.format(date, first_month_date))
#     #
#     # income last 24h, include subscription and target
#     all_income = BaseTransaction.objects.filter(transaction_type__in = ('10', '15', '20', '25'))
#     paid_income = all_income.filter(
#         Q(subscription_transaction__is_paid=True,
#         subscription_transaction__status=SubscriptionTransaction.PAID) | Q(
#         target_transaction__is_paid=True,) | Q(
#         subscription_peyman_transaction__is_paid=True,
#         subscription_peyman_transaction__status=SubscriptionPeymanTransaction.PAID))
#     # last_day_income
#     last_day_income = paid_income.filter(Q(subscription_transaction__paid_date__gt=last_day_date) | Q(
#         target_transaction__created_time__gt=last_day_date) | Q(
#         subscription_peyman_transaction__paid_date__gt=last_day_date)).annotate(
#         business=Case(When(transaction_type__in=('15', '20'),
#                            then=F('subscription_transaction__subscription__business')),
#                       When(transaction_type='10',
#                            then=F('target_transaction__target__business')),
#                       When(transaction_type='25',
#                            then=F('subscription_peyman_transaction__subscription__business'))),
#         phone_number = Case(When(transaction_type__in=('15', '20'),
#                            then=F('subscription_transaction__subscription__business__user__phone_number')),
#                       When(transaction_type__in=('10'),
#                            then=F('target_transaction__target__business__user__phone_number')),
#                       When(transaction_type__in=('25'),
#                            then=F('subscription_peyman_transaction__subscription__business__user__phone_number')))
#         ).values('business', 'phone_number').annotate(
#         last_day_payment=Sum('amount'), count=Count('amount'))
#     # for each businrss that has income last day:
#     for business in last_day_income:
#         if business['last_day_payment'] == 0 or business['phone_number'] is None:
#             continue
#         # last_month_income (first day of month until today)
#         last_month_income = paid_income.filter(Q(subscription_transaction__paid_date__gt=first_month_date,
#             subscription_transaction__subscription__business=business['business']) | Q(
#             target_transaction__created_time__gt=first_month_date,
#             target_transaction__target__business=business['business']) | Q(
#             subscription_peyman_transaction__paid_date__gt=first_month_date,
#             subscription_peyman_transaction__subscription__business=business['business'])).aggregate(
#             last_month_payment=Sum('amount'))
#         # last_day_payment and last_month_income
#         last_day_payment = business['last_day_payment']
#         last_month_income = last_month_income['last_month_payment']
#         # check last_month_income if None
#         if last_month_income is None:
#             last_month_income = 0
#         # logger_2
#         logger.info('business= {0}'.format(business))
#         logger.info('last_day_payment= {0},  last_month_income= {1}'.format(
#             f'{last_day_payment:,}', f'{last_month_income:,}'))
#         #
#         # f'{value:,}' is used for thousands separators
#         # send_business_income_notification
#         send_business_income_notification.delay(
#             business['count'], f'{last_day_payment:,}', f'{last_month_income:,}', business['phone_number'])
#     return last_day_income.count


@shared_task(name='Get given date subscription')
def get_specific_date_subscription_charges(date=None):
    """
     - convert date to the jalali date and get all related subscriptions
     - loop over subscriptions and pass them to the chargers task
    """
    if date is None:
        date = timezone.now()
    jalali_days, jalali_month = get_related_jalali_day_of_month(date)
    subscriptions = Subscription.objects.filter(
        is_enable=True, jalali_due_day_of_month__in=jalali_days, sub_type=Subscription.BANK_APPROACH
    )
    # logger_1
    logger.warning('******** Send Subscription-Transaction SMS <get_specific_date_subscription_charges  *********')
    logger.warning('date= {0},  jalali_days= {1},   jalali_month= {2}'.format(date, jalali_days, jalali_month))
    logger.warning('subscriptions_count= {0}, '.format(subscriptions.count()))
    #
    for subscription in subscriptions:
        last_transaction = subscription.transactions.last()
        if last_transaction is not None and (last_transaction.created_time.date() == date.date()):
            sys.stdout.write("The Subscription Transaction exists with this date\n")
            # logger_2
            logger.warning('---- The Subscription Transaction exists with this date ----')
            #
            continue
        charge_subscription.delay(subscription.id, date=date)
    return subscriptions.count()


@shared_task(name='Get given date direct debit subscription')
def get_specific_date_direct_debit_subscription_charges(date=None):
    if date is None:
        date = timezone.now()
    jalali_days, jalali_month = get_related_jalali_day_of_month(date)
    print('jalali_days: ', jalali_days)
    # max_day = jalali_days[-1]
    # threshold = settings.NUMBER_OF_PEYMAN_CHECK_DAYS
    # min_day = (jalali_days - threshold) if (jalali_days - threshold) > 0 else 1
    subscriptions = Subscription.objects.filter(
        is_enable=True, sub_type=Subscription.PEYMAN_DIRECT_DEBIT,
        # jalali_due_day_of_month__lte=max_day,
        # jalali_due_day_of_month__gte=min_day,
        jalali_due_day_of_month__in=jalali_days,
    )
    print("*** subscriptions ***")
    print(subscriptions)
    for subscription in subscriptions:
        last_transaction = subscription.peyman_transactions.last()
        if last_transaction is not None and (last_transaction.created_time.date() == date.date()) and \
                (last_transaction.status == SubscriptionPeymanTransaction.PAID):
            print("*transaction paid*")
            continue
        direct_debit_charge_subscription.delay(subscription.id, date=date)


@shared_task(name="Execute user direct debit subscription")
def direct_debit_charge_subscription(sid, date=None):
    print("*** START SECOND TASK ***")
    subscription = Subscription.objects.filter(pk=sid, is_enable=True).first()
    if subscription is None:
        return False, "Subscription does not exists and/or is not enable"

    print('subscription: ', subscription)

    if date is None:
        date = timezone.now()
    peyman = subscription.peyman_transactions.first().peyman
    print('peyman: ', peyman)
    print('have_succeed_transaction_in_month: ', peyman.have_succeed_transaction_in_month())
    if not peyman.have_succeed_transaction_in_month():
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

        with transaction.atomic():
            base_transaction = BaseTransaction.objects.create(
                user=subscription.user, amount=subscription.tier.amount, transaction_type=BaseTransaction.DIRECT_DEBIT
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
            send_subscription_notification.delay(subscription.id, notif_type='greeting')
        else:
            number_of_failed = settings.NUMBER_OF_PEYMAN_TRANSACTION_FAILED_FOR_SMS
            if peyman.number_of_failed_transaction_in_month() in number_of_failed:
                # TODO: must be changed with proper SMS pattern
                send_subscription_notification.delay(sid, notif_type='due_date_notify')
        return True, "Task done without error"

    return True, "Already paid"


@shared_task(name="Execute user subscription")
def charge_subscription(sid, date=None):
    subscription = Subscription.objects.filter(pk=sid, is_enable=True).first()
    if subscription is None:
        return False, "Subscription does not exists and/or is not enable"

    if date is None:
        date = timezone.now()

    # str to datetime:
    date = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ')
    # Check existing transactions:
    last_transaction = subscription.transactions.last()
    if last_transaction is not None and (last_transaction.created_time.date() == date.date()):
        print("The Subscription Transaction exists with this date")
        return False, "The Subscription Transaction exists with this date"

    user_wallet = BaseTransaction.wallet(subscription.user)

    # logger_1
    logger.warning('---- charge_subscription (delay_1) ----')
    logger.warning('user={0},  phone_number={1},  user_wallet= {2},  subscription.tier.amount={3}'.format(
        subscription.user.get_full_name(), subscription.user.phone_number, user_wallet, subscription.tier.amount))
    #

    if user_wallet >= subscription.tier.amount:
        # logger_2
        logger.warning('{0} user_wallet is greater >>>'.format(subscription.user.get_full_name()))
        #
        status = SubscriptionTransaction.PAID
        paid_date = timezone.now()
        is_paid = True
    else:
        # logger_3
        logger.warning('{0} user_wallet is lesser <<<'.format(subscription.user.get_full_name()))
        #
        status = SubscriptionTransaction.OWED
        paid_date = None
        is_paid = False
    with transaction.atomic():
        # TODO: due_date should be calculated dynamically
        base_transaction = BaseTransaction.objects.create(
            user=subscription.user, amount=subscription.tier.amount, transaction_type=BaseTransaction.SUBSCRIPTION
        )
        subscription_transaction = SubscriptionTransaction(
            transaction=base_transaction, subscription=subscription,
            due_date=date, status=status, is_paid=is_paid
        )
        if paid_date is not None:
            subscription_transaction.paid_date = paid_date

        if subscription.subscription_purpose is not None:
            subscription_transaction.subscription_purpose = subscription.subscription_purpose
        subscription_transaction.save()

    # logger_4
    logger.warning('user={0}, subscription_transaction.is_paid={1},  paid_date= {2},  status={3}'.format(
        subscription.user.get_full_name(), subscription_transaction.is_paid,
        subscription_transaction.paid_date, subscription_transaction.status))
    #

    if subscription_transaction.is_paid:
        # logger_5
        logger.warning('{} Ready for send_subscription_notification (is_paid=True)'.format(
            subscription.user.get_full_name()))
        #
        send_subscription_notification.delay(subscription.id, notif_type='greeting')
    else:
        # logger_6
        logger.warning('{} Ready for send_subscription_notification (is_paid=False)'.format(
            subscription.user.get_full_name()))
        #
        payment = Payment.create_payment(base_transaction)
        send_subscription_notification.delay(sid, notif_type='due_date_notify', link=payment.get_instant_link())
    return True, "Task done without error"


@shared_task(name="New Send Messages")
def send_subscription_notification(sid, notif_type='greeting', days=0, link="ham3.ir"):
    try:
        subscription = Subscription.objects.get(pk=sid)
    except (Subscription.DoesNotExist, User.DoesNotExist):
        return False, "Subscription and/or User Does not exists"

    templates = dict(
        early_notify='ABREAST-A2',
        due_date_notify='ABREAST-A3',
        greeting='ABREAST-A4',
        late_notify='ABREAST-A1'
    )

    template = templates.get(notif_type, None)
    if template is None:
        return

    link = make_short(link)[8:]

    tokens = dict(
        token10=subscription.user.get_full_name(),
        token20=subscription.business.name,
        token=link
    )

    if notif_type == 'greeting':
        tokens['token'] = subscription.tier.amount
    # logger_1
    logger.warning('+++ {} send_subscription_notification +++'.format(subscription.user.get_full_name()))
    logger.warning('+++ {} notif_type={} +++'.format(subscription.user.get_full_name(), notif_type))
    #
    return send_template_message(subscription.user.phone_number, template, tokens)


@shared_task(name="Send Messages to business owner")
def send_business_income_notification(payment_count, last_day_income, last_month_income, phone_number):
    template = 'ABREAST-A5'
    tokens = dict(
        token=payment_count,
        token2=last_day_income,
        token3=last_month_income,
    )
    print('tokens==', tokens)
    print('phone_number==', phone_number)
    result, message = send_template_message(phone_number, template, tokens)
    print(result, message)
    return result, str(message)


@shared_task(name="Send notification")
def send_subscription_notification_old(sid, notif_type='greeting', days=0, link="ham3.ir"):
    """
        - has two ways for notifications: push and sms
        - has two four types of notification explained before
    :param sid: Subscription model pk
    :param notif_type: available choices: 'early_notify', 'due_date_notify',
    'greeting', 'late_notify'
    :param days: int
    :param link: link to append at the end of message
    :return: send message status
    """
    try:
        subscription = Subscription.objects.get(pk=sid)
    except (Subscription.DoesNotExist, User.DoesNotExist):
        return False, "Subscription and/or User Does not exists"

    templates = dict(
        early_notify='subscription/early_notify.txt',
        due_date_notify='subscription/due_date_notify.txt',
        greeting='subscription/charge_greeting_notify.txt',
        late_notify='subscription/late_notify.txt'
    )
    template = templates.get(notif_type, None)
    if template is None:
        return

    link = make_short(link)[8:]
    # user_full_name = subscription.user.get_full_name()
    context = dict(
        user=subscription.user.get_full_name(), days=days, business=subscription.business.name,
        amount=subscription.tier.amount, tier=subscription.tier.title, link=link,
    )
    message = loader.render_to_string(template, context)
    notify_user(message, subscription.user)


@periodic_task(name='Subscription_charge_handler', run_every=crontab(hour=11, minute=0))
def get_today_due_dates():
    """run every days and call task to get all today due date subscriptions"""
    get_specific_date_subscription_charges.delay()


@periodic_task(name='Direct_debit_charge_handler', run_every=crontab(hour=8, minute=0))
def get_today_direct_debit_due_dates():
    get_specific_date_direct_debit_subscription_charges.delay()


@periodic_task(name='income_report', run_every=crontab(hour=10, minute=0))
def get_today_income_notification():
    """run every days and call task to calculate business income in last 24h and send to project owner """
    get_last_day_subscription_transaction.delay()


# Early notify canceled
# @periodic_task(name='Notify next 3 days subscriptions', run_every=crontab(hour=10, minute=0))
# def early_notify_users_about_subscription(date=None):
#     """
#      - get subscriptions which due_date is exactly next 3 days
#      - check if user has not enough wallet charge notify him
#     """
#     if date is None:
#         date = timezone.now()
#     related_jalali_days, jalali_month = get_related_next_jalali_day_of_month(date)
#     subscriptions = Subscription.objects.filter(is_enable=True, jalali_due_day_of_month__in=related_jalali_days)
#     for subscription in subscriptions:
#         user_wallet = BaseTransaction.wallet(subscription.user)
#         if user_wallet < subscription.tier.amount:
#             transaction = BaseTransaction.objects.create(
#                 user=subscription.user,
#                 amount=subscription.tier.amount,
#                 transaction_type=BaseTransaction.WALLET_CHARGE
#             )
#             payment = Payment.create_payment(transaction)
#             send_subscription_notification(
#                 subscription.id, notif_type='early_notify', days=3, link=payment.get_instant_link()
#             )
#     return subscriptions.count()


@periodic_task(name='Notify past 3 days subscriptions', run_every=crontab(hour=12, minute=0))
def get_late_subscriptions_payment():
    """
        - get unpaid auto generated invoices only for 3 days ago
        - notify user about unpaid invoices
    :return: status of running task
    """
    due_date_min = (timezone.now() - timedelta(days=3)).date()
    due_date_max = (timezone.now() - timedelta(days=2)).date()
    subscription_transactions = SubscriptionTransaction.objects.filter(
        is_paid=False, due_date__gte=due_date_min, due_date__lt=due_date_max, status=SubscriptionTransaction.OWED
    )
    for subscription_transaction in subscription_transactions:
        payment = Payment.create_payment(subscription_transaction.transaction)
        send_subscription_notification.delay(
            subscription_transaction.subscription.id, notif_type='late_notify', days=3, link=payment.get_instant_link()
        )
    return subscription_transactions.count()


@shared_task(name='send register user by business sms')
def send_register_user_by_business_sms(phone, params):
    try:
        result, message = send_template_message(phone, "hamsooRegisterBySms", params)
    except:
        return False
    else:
        return result, str(message)
