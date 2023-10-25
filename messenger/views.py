from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView, ListCreateAPIView, get_object_or_404, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from lib.paginations import MessagesPagination
from messenger.models import MessageBody, MessageAttachment
from messenger.serializers import MessageAttachmentCompleteSerializer, MessageBodyListSerializer, \
    MessageBodyCreateSerializer
from subscription.models import Relation
from user.models import UserProfile
from user.serializers import ProfileLightSerializer

User = get_user_model()


class MessagesList(ListAPIView):
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return MessageBody.objects.filter(Q(sender=self.request.user) | Q(receiver=self.request.user))


class ContactListAPIView(ListAPIView):
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, )
    serializer_class = ProfileLightSerializer

    def get_queryset(self):
        followed = Relation.objects.filter(follower=self.request.user).values_list('following__user__profile', flat=True)
        if self.request.user.profile.role in [UserProfile.CONTENT_PROVIDER, UserProfile.BOTH]:
            followers = Relation.objects.filter(following=self.request.user.business)
            followed = list(followed)
            followed.extend(followers.values_list('follower__profile', flat=True))
        elif self.request.user.profile.role > 3:
            followed = UserProfile.objects.values_list('pk', flat=True)
        return UserProfile.objects.filter(pk__in=followed)


class MessageAttachmentListCreateAPIView(ListCreateAPIView):
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = MessageAttachmentCompleteSerializer

    def get_queryset(self):
        return MessageAttachment.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MessageListCreateAPIView(ListCreateAPIView):
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = MessageBodyListSerializer
    lookup_url_kwarg = 'contact_id'
    pagination_class = MessagesPagination

    def contact(self):
        if getattr(self, '_contact', None) is None:
            contact = get_object_or_404(User.objects.all(), pk=self.kwargs[self.lookup_url_kwarg])
            if not Relation.exists(self.request.user, contact):
                raise PermissionDenied(detail="Permission does not exists")
            setattr(self, '_contact', contact)
        return self._contact

    def get_serializer_class(self):
        if getattr(self, 'request') and self.request.method == "POST":
            return MessageBodyCreateSerializer
        return self.serializer_class

    def get_queryset(self):
        sent = Q(sender=self.request.user, receiver=self.contact())
        received = Q(sender=self.contact(), receiver=self.request.user)
        return MessageBody.objects.filter(sent | received).order_by('-created_time')

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user, receiver=self.contact())


class MessageUpdateAPIView(APIView):
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)

    def put(self, request, pk, *args, **kwargs):
        message = MessageBody.objects.filter(receiver=self.request.user, pk=pk, is_read=False).first()
        if message is not None:
            message.read()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MessageUnreadAPIView(APIView):
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        count = MessageBody.objects.filter(receiver=request.user, is_read=False).count()
        return Response({"count": count}, status=status.HTTP_200_OK)
