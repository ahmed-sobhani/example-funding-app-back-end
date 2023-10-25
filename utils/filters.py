from django.db import models
import operator

from django.utils import six
from rest_framework.filters import SearchFilter
from functools import reduce
from rest_framework.compat import distinct

from utils.format import normalize_text


class PersianFilterBackend(SearchFilter):
    """PersianFilterBackend first normalize input text and remove bad inputs
    then perform search through queryset"""

    def get_search_terms(self, request):
        """Normalize persian search text before trigger search"""
        params = super().get_search_terms(request)
        return [normalize_text(param) for param in params]

    def filter_queryset(self, request, queryset, view):
        search_fields = getattr(view, 'search_fields', None)
        search_terms = self.get_search_terms(request)

        if not search_fields or not search_terms:
            return queryset

        orm_lookups = [
            self.construct_search(six.text_type(search_field))
            for search_field in search_fields
        ]

        base = queryset
        conditions = []
        for search_term in search_terms:
            queries = [
                models.Q(**{orm_lookup: search_term})
                for orm_lookup in orm_lookups
            ]
            conditions.append(reduce(operator.or_, queries))
        queryset = queryset.filter(reduce(operator.and_, conditions))

        if self.must_call_distinct(queryset, search_fields):
            queryset = distinct(queryset, base)
        return queryset
