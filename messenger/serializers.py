from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from django.utils.translation import ugettext_lazy as _

from messenger.models import MessageAttachment, MessageBody


class MessageAttachmentCompleteSerializer(serializers.ModelSerializer):

    class Meta:
        model = MessageAttachment
        fields = ('id', 'attach_file', )


class MessageBodyListSerializer(serializers.ModelSerializer):
    attachment = serializers.SerializerMethodField()

    class Meta:
        model = MessageBody
        fields = ('id', 'sender', 'receiver', 'body', 'attachment', 'is_read', 'created_time')

    def get_attachment(self, obj):
        if obj.attachment is not None:
            request = self.context['request']
            return request.build_absolute_uri(obj.attachment.attach_file.url)
        return None


class MessageBodyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageBody
        fields = ('body', 'attachment')

    def validate_attachment(self, attr):
        if attr.user != self.context['request'].user:
            raise ValidationError(_("Wrong attachment selected"))
        return attr
