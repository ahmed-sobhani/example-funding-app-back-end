from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class UserConfig(AppConfig):
    name = 'user'
    verbose_name = _("User")
    verbose_name_plural = _("Users")

    def ready(self):
        import user.signals
