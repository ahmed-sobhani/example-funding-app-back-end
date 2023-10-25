import firebase_admin
from django.conf import settings
from django.utils.translation import ugettext as _

from firebase_admin import messaging, credentials

from utils.kavenegar import send_sms


def init_firebase():
    try:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
        firebase_admin.initialize_app(cred)
    except:
        pass


def notify_user(message, user):
    devices = user.devices.values_list('notify_token', flat=True)
    data = {
        "title": _("Abreast"),
        # "image": "https://firebase.google.com/images/social.png",
        "message": message
    }
    notification = messaging.Notification(title=_('Abreast'), body=message)
    for device in devices:
        notify_by_push(data, device, notification)
    notify_by_sms(user.phone_number, message)


def notify_by_push(data, token, notification):
    init_firebase()
    try:
        message = messaging.Message(data=data, token=token, notification=notification)
        response = messaging.send(message)
    except ValueError as e:
        print("message error: ValueError:", str(e))
        return str(e)
    except Exception as e:
        print("message error: Exception", str(e))
        return str(e)
    print("message sent successfully:", response)
    return response


def notify_by_sms(phone_number, message):
    result, msg = send_sms(phone_number, message)
    if result:
        print('message sent', msg)
    else:
        print('message not sent', msg)
