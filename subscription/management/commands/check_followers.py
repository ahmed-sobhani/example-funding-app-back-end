from django.core.management.base import BaseCommand

from subscription.models import Subscription, Relation


class Command(BaseCommand):
    help = "Delete tier.amount=0 subscribers & migrate all of them to followers"

    def handle(self, *args, **options):
        print('-' * 80)
        subscriptions = Subscription.objects.filter(is_enable=True)
        print("All active subscriptions:\t", subscriptions.count())
        for subs in subscriptions:
            relation, result = Relation.objects.get_or_create(follower=subs.user, following=subs.business)
            print("business: {}\tsubscription: {}\tsub date: {}\trelation: {}\t".format(
                subs.business.url_path, subs.id, subs.created_time, result
            ))
            subs.save()
        print('-' * 80)
