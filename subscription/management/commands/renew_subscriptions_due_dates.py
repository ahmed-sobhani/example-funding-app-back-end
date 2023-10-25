from django.core.management.base import BaseCommand

from subscription.models import Subscription


class Command(BaseCommand):
    help = "Renew jalali_due_day_of_month for all subscriptions"

    def handle(self, *args, **options):
        print('-'*80)
        subscriptions = Subscription.objects.filter(is_enable=True)
        for subscription in subscriptions:
            subscription.jalali_due_day_of_month = None
            subscription.save()
        print('{} subscriptions updated'.format(subscriptions.count()), '-'*80, sep='\n')