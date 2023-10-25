from datetime import timedelta
from django.utils import timezone

from khayyam import JalaliDatetime


def get_jalali_day_of_month(time):
    """Get georgian datetime, convert it to the jalali format and return .day"""
    jalali_time = convert_to_jalali(time)
    return jalali_time.day


def convert_to_jalali(date):
    """
    convert given georgian datetime to the jalali date time
    :param date: georgian datetime instance
    :return: jalali datetime
    """
    return JalaliDatetime(timezone.localtime(date))


def day_month_ratio(jalali_time):
    """
    aggregate end month days together according to the month in jalali month
    :param jalali_time: converted jalali_date time
    :return: list of integer
    """
    if jalali_time.month == 12 and jalali_time.day == 29:
        return [29, 30, 31]

    if 6 < jalali_time.month < 12 and jalali_time.day == 30:
        return [30, 31]

    return [jalali_time.day]


def get_related_jalali_day_of_month(time):
    """
    this method will auto check end of month days problem in jalali calender
    for example if now is in month 12 of jalali format and today is day 29, we
    should checkout subscriptions with 29, 30 and 31 due_date
    :param time: datetime instance
    :return: list of integer
    """
    jalali_time = convert_to_jalali(time)
    return day_month_ratio(jalali_time), jalali_time.month


def get_related_next_jalali_day_of_month(time):
    """
    this method will find out the next 3 days due_date subscriptions and check
    all month exceptions of georgian calendar, for example if today is day 26
    of month 12 in georgian format all subscriptions with 29, 30 and 31
    due_dates should be notified.
    :param time: datetime instance
    :return: list of integer
    """
    jalali_time = convert_to_jalali(time)
    return day_month_ratio(jalali_time + timedelta(days=3)), jalali_time.month


def get_start_day_of_month(time=timezone.localtime(timezone.now())):
    jalali_time = convert_to_jalali(time)
    start_day = jalali_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start_day.todate()
