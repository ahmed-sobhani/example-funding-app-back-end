from datetime import datetime
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_jwt.serializers import JSONWebTokenSerializer
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.views import JSONWebTokenAPIView, jwt_response_payload_handler

from panel.permissions import IsAdmin
from user.models import UserProfile
from user.serializers import UserRegistrationSerializer, ProfileCompleteSerializer, SetVerifyTokenSerializer, \
    LoginStep1Serializer, LoginStep2Serializer, UserListSerializer

User = get_user_model()


class UserListRegisterAPIView(generics.CreateAPIView, generics.ListAPIView):
    """User complete registration and list API"""
    serializer_class = UserRegistrationSerializer
    queryset = User.objects.filter(profile__role__gte=5)
    permission_classes = (IsAuthenticated, IsAdmin)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)

    def get_serializer_class(self):
        if getattr(self, 'request') and self.request.method.lower() == 'get':
            return UserListSerializer
        return self.serializer_class


class UserUpdateDeleteAPIView(generics.UpdateAPIView):
    """User delete and update API which will fire if pk is sent through url"""
    serializer_class = UserRegistrationSerializer
    queryset = User.objects.filter(profile__role__gte=5)
    permission_classes = (IsAuthenticated, IsAdmin)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)

    def get_serializer_class(self):
        if getattr(self, 'request') and self.request.method.lower() == 'get':
            return UserListSerializer
        return self.serializer_class


class SetVerifyTokenAPIView(generics.CreateAPIView):
    """Create random verify token, save to user model and send it to the user
    on each API call"""
    serializer_class = SetVerifyTokenSerializer
    queryset = User.objects.all()
    # TODO: Throttle needed
    # throttle_classes = ()


class LoginStep1APIView(generics.CreateAPIView):
    """
    only get phone_number and then check if user is previously created or not
    """
    serializer_class = LoginStep1Serializer
    queryset = User.objects.all()
    throttle_scope = 'login_rate'


class LoginStep2APIView(APIView):
    """
    only get phone_number and then check if user is previously created or not
    """
    serializer_class = LoginStep2Serializer
    queryset = User.objects.all()
    throttle_scope = 'login_rate'

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            'request': self.request,
            'view': self,
        }

    def get_serializer_class(self):
        """
        Return the class to use for the serializer.
        Defaults to using `self.serializer_class`.
        You may want to override this if you need to provide different
        serializations depending on the incoming request.
        (Eg. admins get full serialization, others get basic serialization)
        """
        assert self.serializer_class is not None, (
                "'%s' should either include a `serializer_class` attribute, "
                "or override the `get_serializer_class()` method."
                % self.__class__.__name__)
        return self.serializer_class

    def get_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data.get('user') or request.user
            token = serializer.validated_data.get('token')
            response_data = jwt_response_payload_handler(token, user, request)
            response = Response(response_data)
            if api_settings.JWT_AUTH_COOKIE:
                expiration = (datetime.utcnow() +
                              api_settings.JWT_EXPIRATION_DELTA)
                response.set_cookie(api_settings.JWT_AUTH_COOKIE,
                                    token,
                                    expires=expiration,
                                    httponly=True)
            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ObtainJSONWebToken(JSONWebTokenAPIView):
    """
    API View that receives a POST with a user's username and password.
    Returns a JSON Web Token that can be used for authenticated requests.
    """
    serializer_class = JSONWebTokenSerializer
    throttle_scope = 'login_rate'


class ProfileViewSet(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    """Profile complete and update api for users profile which created
    automatically"""
    serializer_class = ProfileCompleteSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)

    def get_object(self):
        return self.request.user.profile

    @action(detail=True, methods=['post'])
    def upgrade_profile(self, request, *args, **kwargs):
        """Change user role from donor to the `both` (donor and provider) by
        calling this API"""
        instance = self.get_object()
        instance.role = instance.BOTH
        instance.save()
        return Response({}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    def update_national_code(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.national_code = request.data.pop('national_code')
        instance.save()
        return Response({'national_code': instance.national_code}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    def identifier_code(self, request, *args, **kwargs):
        identifier_code = request.data.pop('identifier_code')
        if not UserProfile.objects.filter(identifier_code=identifier_code).exists():
            return Response({'identifier_code': 'identifier_code is not exist'}, status=status.HTTP_404_NOT_FOUND)
        instance = self.get_object()
        instance.used_identifier_code = identifier_code
        instance.save()
        return Response({'identifier_code': instance.used_identifier_code}, status=status.HTTP_200_OK)


class APIConfig(APIView):
    def get(self, *args, **kwargs):
        return Response(
            {
                'android': {
                    'version': 2,
                    'update_url': 'https://website.com/',
                    'splash_url': "https://website.com/",
                    'force': False,
                    'description': "",
                    'time': timezone.now()
                },
                'ios': {
                    'version': 2,
                    'update_url': 'https://website.com/',
                    'splash_url': "https://website.com/",
                    'force': False,
                    'description': "",
                    'time': timezone.now()
                }
            }
        )
