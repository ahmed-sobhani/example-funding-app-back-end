from django.core.management.base import BaseCommand
from django.utils import timezone

from subscription.models import Subscription, Relation


class Command(BaseCommand):
    help = "Delete tier.amount=0 subscribers & migrate all of them to followers"

    def handle(self, *args, **options):
        print('-' * 80)
        subscriptions = Subscription.objects.filter(tier__amount=0, is_enable=True)
        print("Empty subscriptions:\t", subscriptions.count())
        for subs in subscriptions:
            relation, result = Relation.objects.get_or_create(follower=subs.user, following=subs.business)
            subs.is_enable = False
            subs.end_date = timezone.now()
            print("business: {}\tsubscription: {}\tstatus: {}\trelation: {}".format(
                subs.business.url_path, subs.id, subs.is_enable, result
            ))
            subs.tier.set_delete()
            subs.save()
        print('-' * 80)
