import datetime
import random
import string

from django.utils import timezone
from django.contrib.auth.models import BaseUserManager
from django.core.validators import validate_comma_separated_integer_list
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core import validators
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, \
    send_mail

from lib.common_model import BaseModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(
            self, username, phone_number, email, password,
            is_staff, is_superuser, **extra_fields
    ):
        """
        Creates and saves a User with the given username, email and password.
        """
        now = timezone.now()
        if not username:
            raise ValueError('The given username must be set')
        email = self.normalize_email(email)
        user = self.model(phone_number=phone_number,
                          username=username, email=email,
                          is_staff=is_staff, is_active=True,
                          is_superuser=is_superuser,
                          date_joined=now, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(
            self, username=None, phone_number=None, email=None,
            password=None, **extra_fields
    ):
        """Create user using provided phone_number or email instead of passing
        username directly"""
        if username is None:
            if email:
                username = email.split('@', 1)[0]
            if phone_number:
                username = random.choice(string.ascii_lowercase) + str(phone_number)[-7:]
            while User.objects.filter(username=username).exists():
                username += str(random.randint(10, 99))

        return self._create_user(username, phone_number, email, password,
                                 False, False, **extra_fields)

    def create_superuser(
            self, username, phone_number, email, password, **extra_fields
    ):
        return self._create_user(username, phone_number, email, password,
                                 True, True, **extra_fields)

    def get_by_phone_number(self, phone_number):
        return self.get(**{'phone_number': phone_number})


class User(AbstractBaseUser, PermissionsMixin):
    """
    An abstract base class implementing a fully featured User model with
    admin-compliant permissions.

    Username, password and email are required. Other fields are optional.
    """
    username = models.CharField(
        verbose_name=_('username'), max_length=32, unique=True,
        help_text=_('Required. 30 characters or fewer starting with a letter. '
                    'Letters, digits and underscore only.'),
        validators=[
            validators.RegexValidator(
                r'^[a-zA-Z][a-zA-Z0-9_\.]+$',
                _('Enter a valid username starting with a-z. '
                  'This value may contain only letters, numbers '
                  'and underscore characters.'), 'invalid'
            ),
        ],
        error_messages={
            'unique': _("A user with that username already exists."),
        }
    )
    first_name = models.CharField(
        verbose_name=_('first name'), max_length=30, blank=True
    )
    last_name = models.CharField(
        verbose_name=_('last name'), max_length=30, blank=True
    )
    email = models.EmailField(
        verbose_name=_('email address'), unique=True, null=True, blank=True
    )
    phone_number = models.BigIntegerField(
        verbose_name=_('mobile number'), unique=True,
        validators=[validators.RegexValidator(regex=r'^989[0-3,9]\d{8}$')],
        error_messages={
            'unique': _("A user with this mobile number already exists."),
        }
    )
    is_staff = models.BooleanField(
        verbose_name=_('staff status'), default=False,
        help_text=_('Designates whether the user can log into this admin site.')
    )
    is_active = models.BooleanField(
        verbose_name=_('active'), default=True,
        help_text=_('Designates whether this user should be treated as active. '
                    'Unselect this instead of deleting accounts.')
    )
    date_joined = models.DateTimeField(
        verbose_name=_('date joined'), auto_created=True
    )
    verify_codes = models.CharField(
        verbose_name=_('verification codes'), max_length=255, blank=True,
        validators=[validate_comma_separated_integer_list]
    )

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'phone_number']

    class Meta:
        db_table = 'user_user'
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """
        Returns the short name for the user.
        """
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email], **kwargs)

    @property
    def is_logged_in_user(self):
        """
        Returns True if user has actually logged in with valid credentials.
        """
        return self.phone_number is not None or self.email is not None

    def get_verify_codes(self):
        if self.verify_codes:
            return self.verify_codes.split(',')
        else:
            return []

    def set_verify_code(self, verify_code):
        """Append new requested verify_code the previous list,
        only last 5 are available"""
        vlist = self.get_verify_codes()
        vlist.append(str(verify_code))
        self.verify_codes = ','.join(vlist[-5:])
        self.save()

    def check_verify_code(self, verify_code):
        """User can authenticate with each verify_code just one time"""
        vlist = self.get_verify_codes()
        new_list = list()
        exists = False
        for code in vlist:
            if code == verify_code:
                exists = True
            else:
                new_list.append(code)
        self.verify_codes = ','.join(new_list)
        self.save()
        return exists

    def save(self, *args, **kwargs):
        if self.email is not None and self.email.strip() == '':
            self.email = None
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    NOT_SELECTED = 0
    MALE = 1
    FEMALE = 2
    GENDER_CHOICES = (
        (NOT_SELECTED, _("Not selected")),
        (MALE, _("Male")),
        (FEMALE, _("Female")),
    )
    DONOR = 1
    CONTENT_PROVIDER = 2
    BOTH = 3
    CALL_CENTER_OPERATOR = 5
    ADMIN = 10
    ROLE_CHOICES = (
        (DONOR, _("Donor")),
        (CONTENT_PROVIDER, _("Content provider")),
        (BOTH, _("Both")),
        (CALL_CENTER_OPERATOR, _("Call center operator")),
        (ADMIN, _("Admin"))
    )
    REJECTED = 5
    CREATED = 10
    APPROVED = 15
    SUSPENDED = 20
    STATUS_CHOICES = (
        (REJECTED, _("Rejected")),
        (CREATED, _("Created")),
        (APPROVED, _("Approved")),
        (SUSPENDED, _("Suspended"))
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    nick_name = models.CharField(verbose_name=_('nick_name'), max_length=150, blank=True)
    avatar = models.ImageField(verbose_name=_('avatar'), blank=True, upload_to='user/avatars/')
    cover_image = models.ImageField(verbose_name=_('cover image'), blank=True, upload_to='user/cover_images/')
    birthday = models.DateField(verbose_name=_('birthday'), null=True, blank=True)
    gender = models.PositiveSmallIntegerField(
        verbose_name=_('gender'), choices=GENDER_CHOICES, default=NOT_SELECTED,
        help_text=_('female is False, male is True, null is unset')
    )
    role = models.PositiveSmallIntegerField(verbose_name=_("Role"), choices=ROLE_CHOICES, default=DONOR)
    status = models.PositiveSmallIntegerField(verbose_name=_("status"), choices=STATUS_CHOICES, default=CREATED)
    verified = models.BooleanField(verbose_name=_("verified"), default=False)
    national_code = models.CharField(_('national code'), max_length=10, blank=True)
    identifier_code = models.CharField(verbose_name=_("identifier_code"), max_length=10, blank=True, null=True,
                                       unique=True,)
    used_identifier_code = models.CharField(verbose_name=_("used_identifier_code"), max_length=10,
                                            blank=True, null=True,)

    class Meta:
        db_table = 'user_profile'
        verbose_name = _('profile')
        verbose_name_plural = _('profiles')

    @property
    def get_first_name(self):
        return self.user.first_name

    @property
    def get_last_name(self):
        return self.user.last_name

    @property
    def get_username(self):
        return self.user.username

    def save(self, *args, **kwargs):
        if not self.identifier_code:
            self.identifier_code = self.generate_code()
        super().save(*args, **kwargs)

    def generate_code(self):
        is_exists = True
        while (is_exists):
            unique_code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            if not UserProfile.objects.filter(identifier_code=unique_code).exists():
                is_exists = False
        return unique_code


class Device(BaseModel):
    user = models.ForeignKey(User, related_name='devices')
    device_uuid = models.UUIDField(_('Device UUID'), unique=True, null=True)
    notify_token = models.CharField(
        _('Notification Token'), max_length=200, blank=True,
        validators=[validators.RegexValidator(r'([a-z]|[A-z]|[0-9])\w+',
                    _('Notify token is not valid'), 'invalid')]
    )

    class Meta:
        db_table = 'users_device'
        verbose_name = _('device')
        verbose_name_plural = _('devices')
