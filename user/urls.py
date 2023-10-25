from django.conf.urls import url
from rest_framework_jwt.views import refresh_jwt_token

from .views import UserListRegisterAPIView, ProfileViewSet, \
    SetVerifyTokenAPIView, ObtainJSONWebToken, LoginStep1APIView, \
    LoginStep2APIView, APIConfig

urlpatterns = [
    # url(r'^register/$', UserRegistrationAPIView.as_view(), name='register'),
    url(r'^config/$', APIConfig.as_view(), name='config'),
    url(r'^login/step_1$', LoginStep1APIView.as_view(), name='login_step_1'),
    url(r'^login/step_2$', LoginStep2APIView.as_view(), name='login_step_2'),
    url(r'^verify-token/$', SetVerifyTokenAPIView.as_view(), name='verify-token'),
    url(r'^obtain-token/', ObtainJSONWebToken.as_view(), name='obtain-token'),
    url(r'^refresh-token/', refresh_jwt_token, name='refresh-token'),
    url(r'^profile/$', ProfileViewSet.as_view({'get': 'retrieve', 'put': 'update'}), name='profile'),
    url(r'^profile/upgrade/$', ProfileViewSet.as_view({'post': 'upgrade_profile'}), name='profile-upgrade'),
    url(r'^profile/identifier-code/$', ProfileViewSet.as_view({'patch': 'identifier_code'}),
        name='profile_identifier_code'),
    url(
        r'^profile/update-national-code/$',
        ProfileViewSet.as_view({'patch': 'update_national_code'}),
        name='profile_national_code'
    )
]
