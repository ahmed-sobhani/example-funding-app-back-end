from datetime import timedelta

from khayyam import JalaliDate, JalaliDatetime


def jalali_date_mapper(months_ago=6):
    """
    Map first and end day of each month in Jalali datetime to with global
    datetime format and return a dict for each month, example:
        [
            {
              'start': datetime.date(2018, 3, 21),
              'end': datetime.date(2018, 4, 20),
              'month': 1, 'year': 2019
            }
        ]
    """
    now = JalaliDate.today()
    month_map = list()
    for i in range(months_ago):
        temp = now - timedelta(days=i * now.daysinmonth)
        month_map.append(
            dict(
                start=JalaliDatetime(temp.year, temp.month, 1, 0, 0, 0, 0).todatetime(),
                end=JalaliDatetime(temp.year, temp.month, temp.daysinmonth, 23, 59, 59, 0).todatetime(),
                month=temp.month, year=temp.year,
            )
        )
    return month_map
