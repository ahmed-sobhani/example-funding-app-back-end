from django.contrib.auth import get_user_model
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, filters
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from business.models import Business
from lib.paginations import PublicBusinessPagination
from subscription.filters import RelationFilter
from subscription.models import Subscription
from subscription.serializers.relation import RelationCreateSerializer, \
    FollowerListSerializer, RelationDetailSerializer
from utils.filters import PersianFilterBackend

User = get_user_model()


class RelationProtectedViewSet(
    mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin, GenericViewSet
):
    """Complete relation handler which will return followers count, follow,
    unfollow followers list and many other APIs"""
    serializer_class = FollowerListSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
    pagination_class = PublicBusinessPagination
    filter_backends = (filters.OrderingFilter, DjangoFilterBackend, PersianFilterBackend,)
    filter_class = RelationFilter
    ordering_fields = ('follower__last_name', 'follower__phone_number', 'created_time')
    search_fields = ('follower__last_name', 'follower__first_name')

    def get_queryset(self):
        business = self.request.user.business
        return business.followers.all().order_by('-created_time')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RelationDetailSerializer
        return self.serializer_class

    def get_serializer_context(self):
        context = super(RelationProtectedViewSet, self).get_serializer_context()
        if self.kwargs.get('slug'):
            context.update({'slug': self.kwargs['slug']})
        return context

    def get_object(self):
        filter_kwargs = {self.lookup_field: self.kwargs['pk']}
        obj = get_object_or_404(User.objects.all(), **filter_kwargs)
        return obj

    def get_business(self):
        filter_kwargs = {'url_path': self.kwargs['slug']}
        business = get_object_or_404(Business.objects.all(), **filter_kwargs)
        return business

    def create(self, request, *args, **kwargs):
        serializer = RelationCreateSerializer(
            data={'following': self.kwargs['slug'], 'follower': request.user.pk}, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        business = self.get_business()
        relation = instance.followings.get(following=business)
        relation.description = request.data.get('description', '')
        relation.save()
        serializer = RelationDetailSerializer(instance, context={'slug': self.kwargs['slug']})
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    def destroy(self, request, *args, **kwargs):
        business = self.get_business()
        if business.subscribers.filter(user=self.request.user).exists():
            return Response(
                {"error": "When you are subscriber cannot unfollow a business"}, status=status.HTTP_400_BAD_REQUEST
            )
        instance = business.followers.filter(follower=self.request.user).first()
        if instance is not None:
            instance.set_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=False, url_path='report')
    def report(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        subscriptions = Subscription.objects.filter(business=request.user.business, is_enable=True)
        data = dict(
            total_users=queryset.count(), total_followers=queryset.count(), subscribe_rate=0,
            total_subscribers=subscriptions.values('user').annotate(Count('user_id')).count(),
        )
        if data['total_subscribers']:
            duration = (subscriptions.last().created_time - subscriptions.first().created_time)
            data['subscribe_rate'] = data['total_subscribers'] / (duration.days + 1)
        return Response(data)


class RelationNonProtectedViewSet(mixins.RetrieveModelMixin, GenericViewSet):
    """Complete relation handler which will return followers count, follow,
    unfollow followers list and many other APIs"""
    serializer_class = RelationCreateSerializer
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)

    def get_business(self):
        filter_kwargs = {'url_path': self.kwargs['slug']}
        business = get_object_or_404(Business.objects.all(), **filter_kwargs)
        return business

    @action(detail=True, methods=['GET'])
    def count(self, request, *args, **kwargs):
        business = self.get_business()
        followed = False
        if self.request.user.is_authenticated:
            followed = business.followers.filter(follower=self.request.user).exists()
        data = {'count': business.followers.count(), 'followed': followed}
        return Response(data)


followers_list = RelationProtectedViewSet.as_view({'get': 'list'})
followers_report = RelationProtectedViewSet.as_view({'get': 'report'})
