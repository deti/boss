import datetime
import random
import string


def update_copy_dict(d:dict, **kwargs) -> dict:
    d = d.copy()
    d.update(kwargs)
    return d

date_format = '%Y-%m-%d'
time_format = '%H:%M:%S'


def generate_token(length:int=5, length_border:int=0, chars:str=string.ascii_letters+string.digits, additional_chars:str=None) -> str:
    """Generate token with settings. Generally used as password generator."""
    if additional_chars:
        chars += additional_chars
    return ''.join(random.sample(chars, random.randint(length-length_border, length+length_border)))


def format_backend_date(date:datetime.date, format:str=date_format) -> str:
    return date.strftime(format)


def format_backend_time(time:datetime.time, format:str=time_format) -> str:
    return time.strftime(format)


def format_backend_datetime(datetime:datetime.datetime, date_format=date_format, time_format=time_format, sep:str='T') -> str:
    return format_backend_date(datetime.date(), date_format) + sep + format_backend_time(datetime.time(), time_format)


def parse_backend_datetime(datetime_:str, date_format=date_format, time_format=time_format) -> str:
    return datetime.datetime.strptime(datetime_, date_format + 'T' + time_format)


def find_first(seq, predicate:callable):
    """Return first item in seq for which predicate(item) is True"""
    return next((x for x in seq if predicate(x)), None)