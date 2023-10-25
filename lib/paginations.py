from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination


class PostLimitPagination(LimitOffsetPagination):
    """
    Limit offset pagination method which is used by content_post pagination API
    """
    default_limit = 16


class CommentLimitPagination(LimitOffsetPagination):
    """
    Limit offset pagination method which is used by content_post's comments
    pagination API
    """
    default_limit = 10


class TransactionPagination(LimitOffsetPagination):
    """
    Limit offset pagination method for Base transactions API
    """
    default_limit = 20


class LightTagsPostPagination(LimitOffsetPagination):
    """
    Limit tags count which will be shown each time on API call
    """
    default_limit = 3


class PublicBusinessPagination(LimitOffsetPagination):
    """
    Limit Business count which will be shown each time on API call
    """
    default_limit = 10


class PublicSubscriptionPurposePagination(LimitOffsetPagination):
    """
    Limit Business count which will be shown each time on API call
    """
    default_limit = 50


class DonorsListPagination(LimitOffsetPagination):
    """
    Limit Business count which will be shown each time on API call
    """
    default_limit = 20


class MessagesPagination(LimitOffsetPagination):
    default_limit = 15
    max_limit = 30


class DefaultPagination(PageNumberPagination):
    """
    Default Pagination with page_size param.
    """
    page_size_query_param = 'page_size'
    page_size = 10
    max_page_size = 30
