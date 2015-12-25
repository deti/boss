import calendar
import datetime
import time
from functools import total_ordering


def datetime_utc_to_timestamp(d):
    if d:
        return calendar.timegm(d.utctimetuple())
    return None


@total_ordering
class TimeLabel(object):
    _time_label_format = "%Y%m%d%H"
    min_label = "2000010100"
    label_length = len(min_label)
    day_label_length = 4 + 2 + 2
    HOUR = 3600

    def __init__(self, timestamp, _label=None):
        if _label:
            self.label = _label
            self._timestamp = timestamp
            self._datetime = None
        else:
            t = None
            d = None
            if isinstance(timestamp, (int, float)):
                label, t = TimeLabel._time_label_from_timestamp(timestamp)
            elif isinstance(timestamp, datetime.date):
                label, d = TimeLabel._time_label_from_datetime(timestamp)
            else:
                raise NotImplementedError("Unknown type {} for time_label".format(type(timestamp)))

            self._timestamp = t
            self._datetime = d
            self.label = label

    def copy(self):
        t = TimeLabel(self._timestamp, _label=self.label)
        t._datetime = self._datetime
        return t

    @staticmethod
    def from_str(time_label):
        t = time.strptime(time_label, TimeLabel._time_label_format)
        t = calendar.timegm(t)
        return TimeLabel(t, _label=time_label)

    def __str__(self):
        return self.label

    def __repr__(self):
        return str(self)

    @property
    def timestamp(self):
        if self._timestamp is None:
            self._timestamp = datetime_utc_to_timestamp(self._datetime)
        return self._timestamp

    @property
    def datetime(self):
        if self._datetime is None:
            self._datetime = datetime.datetime.utcfromtimestamp(self._timestamp)
        return self._datetime

    @staticmethod
    def _time_label_from_timestamp(timestamp):
        timestamp = int(timestamp)
        timestamp -= timestamp % 3600
        t = time.gmtime(timestamp)
        return time.strftime(TimeLabel._time_label_format, t), timestamp

    @staticmethod
    def _time_label_from_datetime(dt):
        if isinstance(dt, datetime.datetime):
            dt = dt.replace(minute=0, second=0, microsecond=0)
        else:
            dt = datetime.datetime.combine(dt, datetime.time())
        return dt.strftime(TimeLabel._time_label_format), dt

    def next(self):
        if self._timestamp is not None:
            return TimeLabel(self._timestamp + self.HOUR)

        return TimeLabel(self._datetime + datetime.timedelta(seconds=self.HOUR))

    def previous(self):
        if self._timestamp is not None:
            return TimeLabel(self._timestamp - self.HOUR)

        return TimeLabel(self._datetime - datetime.timedelta(seconds=self.HOUR))

    def next_day(self):
        if self._timestamp is not None:
            return TimeLabel(self._timestamp + self.HOUR * 24)

        return TimeLabel(self._datetime + datetime.timedelta(days=1))

    def timestamp_range(self):
        return self.timestamp, self.timestamp + self.HOUR - 1

    def datetime_range(self):
        return self.datetime, self.datetime + datetime.timedelta(seconds=self.HOUR - 1)

    def __sub__(self, other):
        return (self.timestamp - other.timestamp) // self.HOUR

    @property
    def day_label(self):
        return self.label[:self.day_label_length]

    @classmethod
    def days(cls, start, end):
        while start.day_label <= end.day_label:
            yield start.day_label
            start = start.next_day()

    def __eq__(self, other):
        return self.label == other.label

    def __lt__(self, other):
        return self.label < other.label

    def __hash__(self):
        return hash(self.label)

