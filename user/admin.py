from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext_lazy as _

from business.admin import BusinessInlineAdmin
from .models import User, UserProfile, Device


class UserProfileInlineAdmin(admin.TabularInline):
    model = UserProfile


class MyUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {
            'fields': ('first_name', 'last_name', 'phone_number', 'email')
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser',
                       'groups', 'user_permissions')
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Verify codes'), {'fields': ('verify_codes',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'phone_number', 'password1', 'password2'),
        }),
    )
    list_display = ('username', 'get_full_name', 'phone_number', 'role','email', 'business')
    search_fields = ('username', 'phone_number', 'first_name', 'last_name')
    inlines = (UserProfileInlineAdmin, BusinessInlineAdmin)

    def role(self, obj):
        return obj.profile.get_role_display()

    def business(self, obj):
        return obj.business.name


class DeviceAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_uuid', 'notify_token']


admin.site.register(User, MyUserAdmin)
admin.site.register(Device, DeviceAdmin)
