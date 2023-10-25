from importlib import import_module

from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from user.models import Device

User = get_user_model()
auth_user_settings = getattr(settings, 'AUTH_USER', {})


def migrate_user(device_uuid, user, notify_token=''):
    if auth_user_settings.get('MIGRATE_ANONYMOUS_USERS'):
        try:
            fake_user = User.objects.get(username=device_uuid.hex)
        except (User.DoesNotExist, ValueError) as e:
            pass
        else:
            move_func_str = auth_user_settings.get('MIGRATE_ANONYMOUS_FUNC')
            if move_func_str:
                try:
                    parts = move_func_str.split('.')
                    module_path, class_name = '.'.join(parts[:-1]), parts[-1]
                    module = import_module(module_path)
                    move_user_func = getattr(module, class_name)
                    move_user_func(user, fake_user)
                except Exception as e:
                    print('User Migrate Error: ', e)

    Device.objects.update_or_create(
        device_uuid=device_uuid, defaults={'user': user, 'notify_token': notify_token}
    )


class SMSBackend(ModelBackend):
    """
    Authenticates against settings.AUTH_USER_MODEL.
    """

    def authenticate(self, username=None, password=None, **kwargs):
        PhoneNumberField = User._meta.get_field('phone_number')
        try:
            phone_number = int(username)
            PhoneNumberField.run_validators(phone_number)
            user = User._default_manager.get_by_phone_number(phone_number)
            if user.check_verify_code(password):
                device_uuid = kwargs.pop('device_uuid', None)
                if device_uuid:
                    migrate_user(
                        device_uuid, user, kwargs.get('notify_token', '')
                    )
                return user
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user (#20760).
            User().set_password(password)
        except (ValueError, ValidationError):
            pass
