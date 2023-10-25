from django.core.management.base import BaseCommand

from utils.notifications.sender import notify_by_push


class Command(BaseCommand):
    help = "Send test push notification to the test device"

    def handle(self, *args, **kwargs):
        print('-' * 80)
        data = {
            "title": "Abreast",
            "message": "abreast test message"
        }
        tokens = ["eFZ2USimaMI:APA91bHoYObuDjy8YLPQ5NYFcfoV-Kcl-z4_SwO8vXPhNTWjFQaUM4o3_uxqH9VW8ID_Je18VO4p463G_VVPLfkQm4q8sKezYloK1yQWQN3Bc4iDHwIC8Z-GzRb01O0uAV_YFIOaUD4X",
                 "cAVioAPiuwY:APA91bESoCnETO63TwkUZ4uuo3HNdq7R56_ui5hSx1OJ6h2Pqv83PlFPUhZc_Er4_r76yWNzCsfCEfzJBiy1jUDTDKxnuzOaK0cNK3Wnr2muqJV_26_boq_drHR6bq4lXq1ZCEk2_hm_"]
        for token in tokens:
            notify_by_push(data, token)
