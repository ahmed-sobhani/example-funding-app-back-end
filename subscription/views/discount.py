from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import get_object_or_404, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from content.models import Post
from lib.common_views import BaseProtectedAPIView
from subscription.models import DiscountCode
from subscription.serializers.discount import DiscountCodeSerializer


class DiscountCodeGeneratorAPIView(BaseProtectedAPIView, APIView):
    """Get or create a discount relation to the user and post, then generate
    and return code to the end user"""
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)

    def get_user_tiers(self, business):
        user = self.request.user
        subscriptions = user.subscriptions.filter(is_enable=True, business=business)
        return subscriptions.values_list('tier', flat=True)

    def get_post(self):
        filter_kwargs = {'pk': self.kwargs['pk']}
        post = get_object_or_404(Post.objects.all(), **filter_kwargs)
        return post

    def post(self, request, *args, **kwargs):
        post = self.get_post()
        user_tiers = self.get_user_tiers(post.business)
        is_owner = (post.user == request.user)
        if not post.discount_allowed:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if not is_owner and post.need_subscription and not len(user_tiers):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        elif not is_owner and post.need_tiers and not post.check_tires(user_tiers):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        discount, result = DiscountCode.objects.get_or_create(
            user=request.user, post=post
        )
        serializer = DiscountCodeSerializer(discount)
        return Response(serializer.data)


class DiscountCodeAPIView(APIView):
    """Get or create a discount relation to the user and post, then generate
    and return code to the end user"""
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    serializer_class = DiscountCodeSerializer
    throttle_scope = "light_rate"
    lookup_field = 'code'

    def get_object(self):
        code = self.request.data.get(self.lookup_field, None)
        if code is None:
            raise Http404
        discount = DiscountCode.decode(code)
        if discount is None:
            raise Http404
        return discount

    def put(self, request, *args, **kwargs):
        discount = self.get_object()
        discount.used = True
        discount.used_time = timezone.now()
        discount.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number', None)
        discount = self.get_object()
        if phone_number is None or discount.user.phone_number != int(phone_number):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        serializer = DiscountCodeSerializer(discount)
        return Response(serializer.data)
