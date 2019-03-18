from datetime import datetime, date, time, timedelta

def get_next_weekday():
    weekday = datetime.weekday(date.today())
    skipdays = 1
    if (weekday == 4):
        skipdays = 3
    if (weekday == 5):
        skipdays = 2
    next_weekday = date.today() + timedelta(days=skipdays)
    return next_weekday

def get_next_saturday():
    weekday = datetime.weekday(date.today())
    skipdays = 5 - weekday
    next_saturday = date.today() + timedelta(days=skipdays)
    return next_saturday

def get_next_sunday():
    weekday = datetime.weekday(date.today())
    skipdays = 6 - weekday
    next_saturday = date.today() + timedelta(days=skipdays)
    return next_saturday

def get_datetime(day, hh, mm):
    return datetime.combine(day, time(hh, mm))

def get_next_weekday_datetime(hh, mm):
    next_weekday_datetime = datetime.combine(get_next_weekday(), time(hh, mm))
    return next_weekday_datetime
