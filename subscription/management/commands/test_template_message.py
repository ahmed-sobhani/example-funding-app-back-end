from django.core.management.base import BaseCommand

from subscription.tasks import send_subscription_notification


class Command(BaseCommand):
    help = "Delete tier.amount=0 subscribers & migrate all of them to followers"

    def add_arguments(self, parser):
        parser.add_argument('subs', type=int)

    def handle(self, *args, **options):
        sid = options['subs']
        print('-' * 80)
        print(send_subscription_notification(sid, notif_type='early_notify', days=0, link="ham3.ir/ea"))
        print(send_subscription_notification(sid, notif_type='due_date_notify', days=0, link="ham3.ir/du"))
        print(send_subscription_notification(sid, notif_type='greeting', days=0, link="ham3.ir"))
        print(send_subscription_notification(sid, notif_type='late_notify', days=0, link="ham3.ir/la"))
        print('-' * 80)
