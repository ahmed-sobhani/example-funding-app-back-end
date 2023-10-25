from rest_framework import serializers

from business.serializers import BusinessLightSerializer
from subscription.models import DiscountCode


class DiscountCodeSerializer(serializers.ModelSerializer):
    phone_number = serializers.IntegerField(source='user.phone_number')
    post = serializers.CharField(source='post.title')
    business = BusinessLightSerializer(source='post.business')

    class Meta:
        model = DiscountCode
        fields = ('business', 'phone_number', 'post', 'used', 'code', 'used_time')
