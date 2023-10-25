import logging
from datetime import timedelta

from celery import shared_task
from celery.schedules import crontab
from celery.task import periodic_task
from django.utils import timezone

from finance.models import Payment, Gateway

logger = logging.getLogger(__file__)

@periodic_task(name='Find failed payments', run_every=crontab(hour=23, minute=30))
def check_failed_payments(from_date=None):
    if from_date is None:
        from_date = timezone.now().today() - timedelta(days=1)

    payments = Payment.objects.filter(
        created_time__gte=from_date, gateway__gateway_code=Gateway.FUNCTION_ZARRINPAL, is_paid=False
    ).values_list('id', flat=True)
    for payment in payments:
        # logger
        logger.info('#### check_failed_payments ####')
        logger.info('from_date= {0},  payment= {1}'.format(from_date, payment))
        #
        recheck_payment.delay(payment)


@shared_task(name="Re-check failed payments")
def recheck_payment(pid):
    try:
        payment = Payment.objects.get(id=pid)
    except Payment.DoesNotExist:
        return "Payment not found"
    if payment.is_paid:
        return "Payment is previously paid"
    payment.verify(None)
    # logger
    logger.info('#### recheck_payment (step_2) ####')
    status_changed = True if payment.status_changed() else False
    logger.info('payment= {0},  status_changed= {1}'.format(payment, status_changed))
    #
    return "{} status changed" if payment.status_changed() else "No change"
