from lib.date_mapper import jalali_date_mapper
from django.db.models import Case, IntegerField, Value, When


def generate_date_conditions(months_ago=6, key='created_time'):
    """Generate date conditions in django_orm way when want to use
    annotate/aggregate in query on Jalali datetime format"""
    cases = list()

    if key == 'paid_date':
        for date in jalali_date_mapper(months_ago=months_ago):
            cases.append(When(paid_date__gte=date['start'], paid_date__lte=date['end'], then=Value(date['month'])))
    elif key == 'subscription_transaction__paid_date':
        for date in jalali_date_mapper(months_ago=months_ago):
            cases.append(When(
                subscription_transaction__paid_date__gte=date['start'],
                subscription_transaction__paid_date__lte=date['end'],
                then=Value(date['month'])))
    elif key == 'subscription_peyman_transaction__paid_date':
        for date in jalali_date_mapper(months_ago=months_ago):
            cases.append(When(
                subscription_peyman_transaction__paid_date__gte=date['start'],
                subscription_peyman_transaction__paid_date__lte=date['end'],
                then=Value(date['month'])))
    else:
        for date in jalali_date_mapper(months_ago=months_ago):
            cases.append(When(created_time__gte=date['start'], created_time__lte=date['end'], then=Value(date['month'])))
    return cases


def generate_date_cases(months_ago=6, key='created_time'):
    """Fetch conditions and init case to be used inside the query manager"""
    conditions = generate_date_conditions(months_ago, key)
    return Case(*conditions, output_field=IntegerField())
