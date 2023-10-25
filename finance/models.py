import json
import uuid

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from finance.utils import zpal_request_handler, zpal_payment_checker
from finance.utils.parsian import parsian_request_handler, parsian_payment_checker
from lib.common_model import BaseModel
from subscription.models import BaseTransaction


class Gateway(BaseModel):
    """
    Save Gateways name and credentials to the db and use them to handle payments
    """

    # CAUTION: do not change bellow function name
    FUNCTION_SAMAN = 'saman'
    FUNCTION_SHAPARAK = 'shaparak'
    FUNCTION_FINOTECH = 'finotech'
    FUNCTION_ZARRINPAL = 'zarrinpal'
    GATEWAY_FUNCTIONS = (
        (FUNCTION_SAMAN, _('Saman')),
        (FUNCTION_SHAPARAK, _('Shaparak')),
        (FUNCTION_FINOTECH, _('FinoTech')),
        (FUNCTION_ZARRINPAL, _("Zarrinpal")),
    )

    title = models.CharField(max_length=100, verbose_name=_("gateway title"))
    gateway_request_url = models.CharField(max_length=150, verbose_name=_("request url"), null=True, blank=True)
    gateway_verify_url = models.CharField(max_length=150, verbose_name=_("verify url"), null=True, blank=True)
    gateway_code = models.CharField(max_length=12, verbose_name=_("gateway code"), choices=GATEWAY_FUNCTIONS)
    is_enable = models.BooleanField(_('is enable'), default=True)
    auth_data = models.TextField(verbose_name=_("auth_data"), null=True, blank=True)

    class Meta:
        verbose_name = _("Gateway")
        verbose_name_plural = _("Gateways")

    def __str__(self):
        return self.title

    def get_request_handler(self):
        handlers = {
            self.FUNCTION_SAMAN: None,
            self.FUNCTION_SHAPARAK: None,
            self.FUNCTION_FINOTECH: None,
            self.FUNCTION_ZARRINPAL: zpal_request_handler,
            self.FUNCTION_PARSIAN: parsian_request_handler,
        }
        return handlers[self.gateway_code]

    def get_verify_handler(self):
        handlers = {
            self.FUNCTION_SAMAN: None,
            self.FUNCTION_SHAPARAK: None,
            self.FUNCTION_FINOTECH: None,
            self.FUNCTION_ZARRINPAL: zpal_payment_checker,
            self.FUNCTION_PARSIAN: parsian_payment_checker,
        }
        return handlers[self.gateway_code]

    @property
    def credentials(self):
        return json.loads(self.auth_data)


class Payment(BaseModel):
    invoice_number = models.UUIDField(verbose_name=_("invoice number"), unique=True, default=uuid.uuid4)
    amount = models.PositiveIntegerField(verbose_name=_("payment amount"), editable=True)
    gateway = models.ForeignKey(Gateway, related_name="payments", null=True, blank=True, verbose_name=_("gateway"))
    is_paid = models.BooleanField(verbose_name=_("is paid status"), default=False)
    payment_log = models.TextField(verbose_name=_('logs'), blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'), null=True)
    transaction = models.OneToOneField(BaseTransaction, verbose_name=_("transaction"), related_name='payment')
    authority = models.CharField(max_length=64, verbose_name=_("authority"), blank=True)

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")

    def __str__(self):
        return self.invoice_number.hex

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._b_is_paid = self.is_paid

    @property
    def bank_page(self):
        handler = self.gateway.get_request_handler()
        if handler is not None:
            return handler(self.gateway, self)

    @property
    def title(self):
        return _("Instant payment")

    @property
    def detail(self):
        return self.transaction.title

    def status_changed(self):
        return self.is_paid != self._b_is_paid

    def verify(self, data):
        handler = self.gateway.get_verify_handler()
        if not self.is_paid and handler is not None:
            handler(self, data)
        return self.is_paid

    def get_absolute_url(self):
        return 'https://website.com/dashboards?invoice={}#wallet'.format(self.invoice_number)

    def get_gateway(self):
        gateway = Gateway.objects.filter(is_enable=True).first()
        return gateway.gateway_code

    def get_instant_link(self):
        return 'https://website.com/finance/pay/{}/{}/'.format(self.invoice_number, self.get_gateway())

    def is_wallet_charge(self):
        if self.transaction is None:
            return True
        has_subscription = hasattr(self.transaction, 'subscription_transaction')
        has_target = hasattr(self.transaction, 'target_transaction')
        return not (has_subscription or has_target)

    @classmethod
    def create_payment(cls, transaction):
        if hasattr(transaction, 'payment'):
            return getattr(transaction, 'payment')
        return cls.objects.create(amount=transaction.amount, user=transaction.user, transaction=transaction)

    def save_log(self, data, scope='Request handler', save=True):
        generated_log = "[{}][{}] {}\n".format(timezone.now(), scope, data)
        if self.payment_log != '':
            self.payment_log += generated_log
        else:
            self.payment_log = generated_log
        if save:
            self.save()

    def clone(self):
        transaction = self.transaction
        transaction.id = None
        transaction.payment = None
        transaction.transaction_type = transaction.WALLET_CHARGE
        transaction.save()
        return Payment.create_payment(transaction)
