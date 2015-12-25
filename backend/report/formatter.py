from babel.dates import LC_TIME, format_date, format_datetime
from babel.numbers import format_number
from datetime import timedelta, datetime
from babel.core import Locale
from utils.i18n import localize_money

TIMEDELTA_UNITS = (
    ('year',   3600 * 24 * 365, 2),
    ('month',  3600 * 24 * 30, 2),
    ('day',    3600 * 24, 1),
    ('hour',   3600, 1),
    ('minute', 60, 1),
    ('second', 1, 1)
)


# noinspection PyShadowingBuiltins
def format_timedelta(delta, granularity='second', threshold=1.,
                     format='medium', locale=LC_TIME, deep=3):
    """Return a time delta according to the rules of the given locale.

    >>> format_timedelta(timedelta(weeks=12), locale='en_US')
    u'3 months'
    >>> format_timedelta(timedelta(seconds=1), locale='es')
    u'1 segundo'

    The granularity parameter can be provided to alter the lowest unit
    presented, which defaults to a second.

    >>> format_timedelta(timedelta(hours=3), granularity='day',
    ...                  locale='en_US')
    u'1 day'

    The threshold parameter can be used to determine at which value the
    presentation switches to the next higher unit. A higher threshold factor
    means the presentation will switch later. For example:

    >>> format_timedelta(timedelta(hours=23), threshold=0.9, locale='en_US')
    u'1 day'
    >>> format_timedelta(timedelta(hours=23), threshold=1.1, locale='en_US')
    u'23 hours'

    In addition directional information can be provided that informs
    the user if the date is in the past or in the future:

    >>> format_timedelta(timedelta(hours=1), add_direction=True)
    u'In 1 hour'
    >>> format_timedelta(timedelta(hours=-1), add_direction=True)
    u'1 hour ago'

    :param delta: a ``timedelta`` object representing the time difference to
                  format, or the delta in seconds as an `int` value
    :param granularity: determines the smallest unit that should be displayed,
                        the value can be one of "year", "month", "week", "day",
                        "hour", "minute" or "second"
    :param threshold: factor that determines at which point the presentation
                      switches to the next higher unit
    :param format: the format (currently only "medium" and "short" are supported)
    :param locale: a `Locale` object or a locale identifier
    """
    if format not in ('short', 'medium'):
        raise TypeError('Format can only be one of "short" or "medium"')
    if threshold < 1.:
        raise TypeError("Threshold should be more or equal than 1.0")
    if isinstance(delta, timedelta):
        seconds = int((delta.days * 86400) + delta.seconds)
    else:
        seconds = delta
    locale = Locale.parse(locale)

    def _iter_choices(value):
        yield value + ':' + format
        yield value

    result = []
    seconds = abs(seconds)
    for unit, secs_per_unit, unit_threshold in TIMEDELTA_UNITS:
        value = seconds / secs_per_unit
        if value >= max(threshold, unit_threshold) or unit == granularity:
            if unit == granularity and value > 0:
                value = max(1, value)
            value = int(round(value))
            plural_form = locale.plural_form(value)

            deep -= 1
            seconds -= value * secs_per_unit

            pattern = None
            for choice in _iter_choices(unit):
                patterns = locale._data['unit_patterns'].get(choice)
                if patterns is not None:
                    pattern = patterns[plural_form]
                    break
            assert pattern
            result.append(pattern.replace('{0}', str(value)))

        if unit == granularity or deep == 0 or seconds == 0:
            break

    return u' '.join(result)


class LocaleFormatter(object):
    def __init__(self, locale):
        self.locale = locale

    def timedelta(self, interval):
        if isinstance(interval, int):
            interval = timedelta(seconds=interval)
            interval = format_timedelta(interval, locale=self.locale)
        elif isinstance(interval, timedelta):
            interval = format_timedelta(interval, locale=self.locale)
        return interval

    def money(self, m, currency):
        return localize_money(m, currency, self.locale)

    def date(self, d):
        if isinstance(d, int):
            d = datetime.fromtimestamp(d)
            d = format_date(d, locale=self.locale)
        return d

    def datetime(self, d):
        if isinstance(d, int):
            d = datetime.utcfromtimestamp(d)
            d = format_datetime(d, locale=self.locale)
        return d

    def float(self, number):
        print(number)
        if isinstance(number, float):
            print(number, format_number(number, locale=self.locale), self.locale)
            return format_number(number, locale=self.locale)
        return number
