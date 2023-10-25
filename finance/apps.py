from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class FinanceConfig(AppConfig):
    name = 'finance'
    verbose_name = _("Finance")
    verbose_name_plural = _("Finances")

    def ready(self):
        import finance.signals
