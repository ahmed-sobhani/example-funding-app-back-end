from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from khayyam import JalaliDatetime


class BaseModelManager(models.Manager):
    def get_queryset(self):
        return super(BaseModelManager, self).get_queryset().filter(deleted=False)


class BaseModel(models.Model):
    created_time = models.DateTimeField(verbose_name=_('created time'), auto_now_add=True)
    modified_time = models.DateTimeField(verbose_name=_('modified time'), auto_now=True)
    deleted_time = models.DateTimeField(verbose_name=_('deleted time'), null=True, blank=True, editable=False)
    deleted = models.BooleanField(verbose_name=_('deleted'), default=False, editable=False)

    objects = BaseModelManager()
    private_manager = models.Manager()

    class Meta:
        abstract = True

    @property
    def jalali_created_time(self):
        return JalaliDatetime(timezone.localtime(self.created_time)).strftime('%H:%M %y/%m/%d')

    @property
    def jalali_modified_time(self):
        return JalaliDatetime(timezone.localtime(self.modified_time)).strftime('%H:%M %y/%m/%d')

    def set_delete(self):
        """Perform safe delete to the all models objects"""
        self.deleted = True
        self.deleted_time = timezone.now()
        self.save()
