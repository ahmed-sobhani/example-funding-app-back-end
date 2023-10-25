from rest_framework.generics import ListAPIView, RetrieveAPIView


class BasePublicListAPIView(ListAPIView):
    """To read business related models and credentials one single flow is needed
    and according to DRY, all instructions will aggregate here,
    Return list response"""
    lookup_field = 'business__url_path'
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        filter_query = {self.lookup_field: self.kwargs[self.lookup_url_kwarg]}
        return self.queryset.filter(**filter_query)


class BasePublicRetrieveAPIView(RetrieveAPIView):
    """To read business related models and credentials one single flow is needed
    and according to DRY, all instructions will aggregate here,
    Return single response"""
    lookup_field = 'url_path'
    lookup_url_kwarg = 'slug'


class BaseProtectedAPIView:
    def get_serializer_context(self):
        """Add user's subscriptions to the serializer context"""
        context = super().get_serializer_context()
        if getattr(self, 'request'):
            user = getattr(self.request, 'user', None)
            if user.is_authenticated and user.is_active:
                if getattr(self, 'lookup_field') and getattr(self, 'lookup_url_kwarg'):
                    subscriptions = user.subscriptions.filter(**{self.lookup_field: self.kwargs[self.lookup_url_kwarg]})
                else:
                    subscriptions = user.subscriptions.all()
                context['tiers'] = [subscription.tier.id for subscription in subscriptions if subscription.is_active]
            else:
                context['tiers'] = []
            context['subscribed'] = bool(len(context['tiers']))
        return context
