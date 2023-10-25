from django.core.management.base import BaseCommand
from subscription.models import Subscription


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        print("test start")
        try:
            subscription = Subscription.objects.get(
                is_enable=True, sub_type=Subscription.PEYMAN_DIRECT_DEBIT,
                # jalali_due_day_of_month__lte=max_day,
                # jalali_due_day_of_month__gte=min_day,
                jalali_due_day_of_month=3,
                tier__amount=5000,
            )
        except Subscription.DoesNotExist:
            print("not found")
        else:
            print("* subscription info *")
            print("subscription: ", subscription)
            print(subscription.id)
            print(subscription.user)
            print(subscription.business)
            print(subscription.tier)
            print(subscription.subscription_purpose)
            print(subscription.is_enable)
            print(subscription.sub_type)
            print("* subscription info *")
