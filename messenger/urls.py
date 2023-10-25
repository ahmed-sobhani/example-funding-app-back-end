from django.conf.urls import url

from messenger.views import MessageAttachmentListCreateAPIView, MessageListCreateAPIView, ContactListAPIView, \
    MessageUpdateAPIView, MessageUnreadAPIView

urlpatterns = [
    url(r'attachment/$', MessageAttachmentListCreateAPIView.as_view(), name='create_attachment'),
    url(r'contacts/$', ContactListAPIView.as_view(), name='contacts'),
    url(r'messages/list/$', MessageListCreateAPIView.as_view(), name='messages_list'),
    url(r'messages/(?P<contact_id>[0-9].+)/$', MessageListCreateAPIView.as_view(), name='message_room'),
    url(r'messages/read/(?P<pk>[0-9].*)/$', MessageUpdateAPIView.as_view(), name='read_messages'),
    url(r'messages/count/$', MessageUnreadAPIView.as_view(), name='messages_count'),
]
