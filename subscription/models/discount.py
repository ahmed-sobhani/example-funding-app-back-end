from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import ugettext_lazy as _

from content.models import Post
from lib.common_model import BaseModel
from utils.discount import DigitEncoder

User = get_user_model()


class DiscountCode(BaseModel):
    """Store all generated discount codes here"""
    user = models.ForeignKey(
        User, related_name='discounts', verbose_name=_("user")
    )
    post = models.ForeignKey(
        Post, related_name='discounts', verbose_name=_("post")
    )
    used = models.BooleanField(default=False, verbose_name=_("used"))
    used_time = models.DateTimeField(
        verbose_name=_("used time"), null=True, blank=True
    )

    class Meta:
        verbose_name = _("DiscountCode")
        verbose_name_plural = _("DiscountCodes")

    def __str__(self):
        return "{}: {}".format(str(self.user), str(self.post))

    @property
    def code(self):
        return DigitEncoder().encode_id(self.pk)

    @classmethod
    def decode(cls, code):
        try:
            pk = DigitEncoder().decode_id(code)
            discount = cls.objects.get(pk=pk)
        except:
            discount = None
        return discount
