from random import randint

from django.contrib.auth import get_user_model, authenticate
from django.core import validators
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_jwt.compat import PasswordField, get_username_field
from rest_framework_jwt.serializers import jwt_payload_handler, \
    jwt_encode_handler

from subscription.models import BaseTransaction
from subscription.serializers.subscriptions import SubscriptionLightSerializer
from user.models import UserProfile
from user.tasks import send_verification_code

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """User registration serializer"""
    fullname = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(
        required=True, validators=[validators.RegexValidator(regex=r'^989[0-3,9]\d{8}$')]
    )
    # role = serializers.IntegerField(write_only=True, default=1)

    class Meta:
        model = User
        fields = ('phone_number', 'username', 'fullname', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, attrs):
        if getattr(self, 'instance', None) is None and User.objects.filter(phone_number=attrs['phone_number']).exists():
            raise ValidationError(_("Phone number already exists"))

        fullname = attrs.pop('fullname')
        fullname_strip = fullname.split()
        attrs['first_name'] = fullname_strip[0]
        if len(fullname_strip) > 1:
            attrs['last_name'] = ' '.join(fullname_strip[1:])
        return attrs

    # def update(self, instance, validated_data):
    #     if 'phone_number' in validated_data:
    #         validated_data.pop('phone_number')
    #     return super().update(instance, validated_data)

    def create(self, validated_data):
        # role = validated_data.pop('role')
        user = User.objects.create_user(**validated_data)
        user.profile.role = UserProfile.CALL_CENTER_OPERATOR
        user.profile.save()
        return user


class LoginStep1Serializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(
        required=True,
        validators=[validators.RegexValidator(regex=r'^989[0-3,9]\d{8}$')]
    )
    role = serializers.IntegerField(write_only=True, default=1)
    verified = serializers.BooleanField(source='profile.verified', read_only=True)

    class Meta:
        model = User
        fields = ('phone_number', 'role', 'verified')

    def validate(self, attrs):
        user = User.objects.filter(phone_number=attrs['phone_number']).first()
        if not user:
            user = User.objects.create_user(phone_number=attrs['phone_number'])

        if not user.profile.verified:
            user.profile.role = attrs['role']
            user.profile.save()
        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        send_verification_code.delay(validated_data['user'].id)
        return validated_data['user']


class LoginStep2Serializer(serializers.Serializer):
    """Just add fullname to the default JWT token serializer and update
    user data if sent credentials are True"""

    def __init__(self, *args, **kwargs):
        super(LoginStep2Serializer, self).__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField()
        self.fields['password'] = PasswordField(write_only=True)
        self.fields['fullname'] = serializers.CharField(
            write_only=True, required=False
        )
        self.fields['device_uuid'] = serializers.UUIDField(
            write_only=True, required=False
        )
        self.fields['notify_token'] = serializers.CharField(
            write_only=True, required=False, allow_null=True
        )

    @property
    def username_field(self):
        return get_username_field()

    def validate(self, attrs):
        credentials = {
            self.username_field: attrs.get(self.username_field),
            'password': attrs.get('password')
        }

        if attrs.get('device_uuid'):
            credentials['device_uuid'] = attrs.get('device_uuid')

        if attrs.get('notify_token'):
            credentials['notify_token'] = attrs.get('notify_token')

        if all(credentials.values()):
            user = authenticate(**credentials)

            if user:
                if not user.is_active:
                    msg = _('User account is disabled.')
                    raise serializers.ValidationError(msg)
                if not user.profile.verified:
                    fullname = attrs.pop('fullname', '')
                    if fullname == '':
                        user.set_verify_code(attrs.get('password'))
                        raise ValidationError(_("Fullname should be submitted"))
                    fullname_strip = fullname.split()
                    user.first_name = fullname_strip[0]
                    if len(fullname_strip) > 1:
                        user.last_name = ' '.join(fullname_strip[1:])
                    user.save()
                    user.profile.verified = True
                    user.profile.save()

                payload = jwt_payload_handler(user)

                return {
                    'token': jwt_encode_handler(payload),
                    'user': user
                }
            else:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg)
        else:
            msg = _('Must include "{username_field}" and "password".')
            msg = msg.format(username_field=self.username_field)
            raise serializers.ValidationError(msg)


class SetVerifyTokenSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(
        required=True,
        validators=[validators.RegexValidator(regex=r'^989[0-3,9]\d{8}$')]
    )

    class Meta:
        model = User
        fields = ('phone_number',)

    def validate_phone_number(self, attr):
        if not User.objects.filter(phone_number=attr).exists():
            raise ValidationError(_("User is not registered"))
        return attr

    def create(self, validated_data):
        phone_number = validated_data['phone_number']
        user = User.objects.get(phone_number=phone_number)
        send_verification_code.delay(user.id)
        return user


class UserLightSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source='get_full_name')
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'fullname', 'avatar',)

    def get_avatar(self, obj):
        try:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.profile.avatar.url)
        except Exception as error:
            return None

class UserCompleteSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source='get_full_name', required=False)

    class Meta:
        model = User
        fields = ('email', 'phone_number', 'fullname')
        extra_kwargs = {
            'phone_number': {'validators': [], 'read_only': True},
            'email': {'validators': []},
        }

    def update(self, instance, validated_data):
        if User.objects.filter(email=validated_data.get('email')).exclude(id=instance.id).exists():
            raise ValidationError(_("This email address already exists"))
        return super().update(instance, validated_data)


class UserListSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source='get_full_name', required=False)
    role = serializers.CharField(source='profile.role')

    class Meta:
        model = User
        fields = ('id', 'fullname', 'username', 'phone_number', 'role', 'is_active')


class ProfileLightSerializer(serializers.ModelSerializer):
    user = UserLightSerializer()

    class Meta:
        model = UserProfile
        fields = ('user', 'nick_name', 'avatar', 'gender', 'role')


class ProfileCompleteSerializer(serializers.ModelSerializer):
    user = UserCompleteSerializer()
    wallet = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ('nick_name', 'avatar', 'gender', 'role', 'user', 'wallet', 'national_code',
                  'identifier_code', 'used_identifier_code')

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        instance = super().update(instance, validated_data)

        if user_data:
            fullname = user_data.pop('get_full_name')
            fullname_strip = fullname.split()
            extra_data = dict(first_name=fullname_strip[0])
            if len(fullname_strip) > 1:
                extra_data['last_name'] = ' '.join(fullname_strip[1:])
            user_serializer = UserCompleteSerializer(instance.user, data=user_data)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save(**extra_data)
        return instance

    def get_wallet(self, obj):
        return BaseTransaction.wallet(obj.user)


class DonorListSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source='get_full_name')
    role = serializers.IntegerField(source='profile.role')
    total_paid = serializers.SerializerMethodField()
    subscriptions = SubscriptionLightSerializer(many=True)

    class Meta:
        model = User
        fields = ('fullname', 'phone_number', 'role', 'date_joined', 'is_active', 'total_paid', 'subscriptions')

    def get_total_paid(self, obj):
        return obj.transactions.aggregate(t=Coalesce(Sum("amount"), 0))['t']


class BestProvidersSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source='get_full_name')
    role = serializers.IntegerField(source='profile.role')
    total_post = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    url_path = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('fullname', 'phone_number', 'role', 'date_joined', 'total_post', 'title', 'category', 'avatar', 'url_path',)

    def get_total_post(self, obj):
        return obj.posts.count()

    def get_title(self, obj):
        return obj.business.name

    def get_category(self, obj):
        return obj.business.category.name

    def get_avatar(self, obj):
        request = self.context.get('request')
        try:
            return request.build_absolute_uri(obj.business.avatar.url)
        except:
            return None

    def get_url_path(self, obj):
        return obj.business.url_path
