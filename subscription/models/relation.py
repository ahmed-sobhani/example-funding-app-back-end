from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q

from business.models import Business

from django.utils.translation import ugettext_lazy as _

from lib import fields
from lib.common_model import BaseModel


User = get_user_model()


class Relation(BaseModel):
    """Main model to store follower/following relationships in single,
    standalone table for separate Views and Serializers"""
    follower = models.ForeignKey(User, related_name='followings', verbose_name=_("Follower"))
    following = models.ForeignKey(Business, related_name="followers", verbose_name=_("following"))
    description = fields.FarsiTextField(verbose_name=_('description'), blank=True)

    class Meta:
        verbose_name = _("Relation")
        verbose_name_plural = _("Relations")

    def __str__(self):
        return "{} > {}".format(str(self.follower), str(self.following))

    @classmethod
    def exists(cls, user_1, user_2):
        relations = list()
        if hasattr(user_1, 'business'):
            relations.append(cls.objects.filter(follower=user_2, following=user_1.business).exists())
        if hasattr(user_2, 'business'):
            relations.append(cls.objects.filter(follower=user_1, following=user_2.business).exists())
        if user_1.profile.role > 3 or user_2.profile.role > 3:
            relations.append(True)
        return any(relations)
