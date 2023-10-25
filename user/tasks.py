from celery import shared_task
from django.contrib.auth import get_user_model

from user.utils import generate_verify_code
from utils.kavenegar import send_verify_message

User = get_user_model()


@shared_task()
def send_verification_code(uid):
    try:
        user = User.objects.get(pk=uid)
    except User.DoesNotExist():
        return False
    else:
        verify_code = generate_verify_code(user)
        result, message = send_verify_message(user.phone_number, verify_code)
        return result, str(message)
