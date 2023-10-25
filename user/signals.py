from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from user.models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile for each user in creation time"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=UserProfile)
def create_user_business(sender, instance, created, **kwargs):
    """Create Business for each user has content provider ro both role, when
    user role is bigger than donor must have business to avoid internal
    server error"""
    if instance.role > 1:
        pass
