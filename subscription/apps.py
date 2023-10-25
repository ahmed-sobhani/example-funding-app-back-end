from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class SubscriptionConfig(AppConfig):
    name = 'subscription'
    verbose_name = _("subscription")
    verbose_name_plural = _("subscriptions")

    def ready(self):
        import subscription.signals
