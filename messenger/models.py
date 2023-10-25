from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _

from lib.common_model import BaseModel
from lib.fields import FarsiTextField

User = get_user_model()


class MessageAttachment(BaseModel):
    attach_file = models.FileField(
        upload_to='messages/attachments/', verbose_name=_('attach_file'),
        validators=[FileExtensionValidator(
            allowed_extensions=['mp4', '3gp', 'wmv', 'webm', 'flv', 'mpeg', 'jpg', 'png', 'jpeg']
        )]
    )
    user = models.ForeignKey(User, related_name='message_attachments', verbose_name=_('user'))

    class Meta:
        verbose_name = _("MessageAttachment")
        verbose_name_plural = _("MessageAttachments")

    def __str__(self):
        return self.user.username


class MessageBody(BaseModel):
    sender = models.ForeignKey(User, related_name='sent_messages', verbose_name=_('sender'))
    receiver = models.ForeignKey(User, related_name='receiver_messages', verbose_name=_('receiver'))
    body = FarsiTextField(verbose_name=_('body'))

    attachment = models.ForeignKey(
        MessageAttachment, blank=True, null=True, verbose_name=_("attachment"), related_name='messages'
    )
    is_read = models.BooleanField(verbose_name=_('is read'), default=False)

    class Meta:
        verbose_name = _("MessageBody")
        verbose_name_plural = _("MessageBodies")

    def __str__(self):
        return "{} >> {}".format(self.sender.username, self.receiver.username)

    def read(self):
        self.is_read = True
        self.save()
        return self.is_read
