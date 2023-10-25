from django import template

register = template.Library()


@register.filter(name='persian_int')
def persian_int(english_int):
    persian_nums = ('۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹')
    number = str(english_int)
    temp = []
    for i in number:
        try:
            temp.append(persian_nums[int(i)])
        except:
            temp.append(i)
    return ''.join(temp)
