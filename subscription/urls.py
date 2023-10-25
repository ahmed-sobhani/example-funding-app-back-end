from django.conf.urls import url

from subscription.views import SubscriptionListCreateAPIView, SubscriptionChartAPIView, SubscriptionTableListAPIView
from subscription.views.discount import DiscountCodeAPIView, DiscountCodeGeneratorAPIView
from subscription.views.relation import RelationProtectedViewSet, RelationNonProtectedViewSet
from subscription.views.subscriptions import TargetTransactionAPIView, SubscriberAPIView, UserValidationForSubscription, \
    SubscriptionInviteAPIView, RegisterUserWithTierCreateAPIView
from subscription.views.transactions import TransactionsListAPIView, DonorsTransactionListAPIView, \
    TransactionsChartAPIView, DonorsTransactionReportAPIView, TargetTransactionListAPIView, \
    DonorsTransactionListAPIViewV2, DonorsTransactionListAPIViewV3

urlpatterns = [
    url(r'list/$', SubscriptionListCreateAPIView.as_view(), name='subscriptions-list'),
    url(r'validation/$', UserValidationForSubscription.as_view(), name='subscriptions-validation'),
    url(r'create/$', SubscriptionListCreateAPIView.as_view(), name='create-subscription'),
    url(r'target/$', TargetTransactionAPIView.as_view(), name='target-transaction'),
    url(r'disable/$', SubscriptionListCreateAPIView.as_view(), name='disable-subscription'),
    url(r'subscriber/(?P<slug>.*)/$', SubscriberAPIView.as_view(), name='subscriber-report'),
    url(r'subscribers/chart/$', SubscriptionChartAPIView.as_view(), name='subscribers-chart'),
    url(r'subscribers/table/$', SubscriptionTableListAPIView.as_view(), name='subscribers-table'),
    url(r'transactions/chart/$', TransactionsChartAPIView.as_view(), name='transactions-chart'),
    url(r'transactions/table/$', DonorsTransactionListAPIView.as_view(), name='transactions-table'),
    url(r'transactions/table/v2/$', DonorsTransactionListAPIViewV2.as_view(), name='transactions-table-v2'),
    url(r'transactions/table/v3/$', DonorsTransactionListAPIViewV3.as_view(), name='transactions-table-v3'),
    url(r'transactions/table/report/$', DonorsTransactionReportAPIView.as_view(), name='transactions-table-report'),
    url(r'transactions/$', TransactionsListAPIView.as_view(), name='transactions'),
    url(r'transactions/target/table/$', TargetTransactionListAPIView.as_view(), name='target-transactions'),
    url(r'relation/(?P<slug>.*)/follow/$', RelationProtectedViewSet.as_view({'post': 'create'}, name='follow')),
    url(r'relation/(?P<slug>.*)/unfollow/$', RelationProtectedViewSet.as_view({'delete': 'destroy'}, name='unfollow')),
    url(r'relation/(?P<slug>.*)/(?P<pk>[0-9].*)/$', RelationProtectedViewSet.as_view({'get': 'retrieve', 'patch': 'update'}, name='detail')),
    url(r'relation/(?P<slug>.*)/count/$', RelationNonProtectedViewSet.as_view({'get': 'count'}, name='followers-count')),
    url(r'discount/(?P<pk>[0-9].*)/$', DiscountCodeGeneratorAPIView.as_view(), name='discount-generator'),
    url(r'discount/$', DiscountCodeAPIView.as_view(), name='discount'),
    url(r'invite/(?P<slug>.*)/$', SubscriptionInviteAPIView.as_view(), name='invite'),
    url(r'user/register/active-tier/$', RegisterUserWithTierCreateAPIView.as_view(), name='user-register-active-tier')
]
