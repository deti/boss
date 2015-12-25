import bisect
import re
import time
import logbook
import datetime
from utils import grouped
from calendar import timegm

class WeightSegments(object):
    """
    This class stores and managements set of weight segments.

    The segments are stored in two arrays:
        * edges -- contains sequence left and rights edges of segments.
                   The even elements in the list are left segment edges and odd elements are rights segment edges
        * weights -- list of weights for each segment

    The size of edges is 2*<segment count> and size of weights is <segment count>.

    """
    serialize_time_format = "%Y%m%d %H:%M:%S"

    def __init__(self, deviation, edges=None, weights=None):
        """
        :param deviation: If the distance between two neighbor segments less than this value,
                          then they will be merged to one segment
        :param edges: List of edges
        :param weights: List of weights
        """
        if edges:
            assert len(edges) == len(weights)*2

        self.edges = edges or []
        self.deviation = deviation
        self.weights = weights or []

    def __eq__(self, other):
        return self.deviation == other.deviation and self.edges == other.edges and \
            self.weights == other.weights

    @staticmethod
    def timestamps_to_str(ts, short=False):
        if short:
            format_str = WeightSegments.serialize_time_format
        else:
            format_str = "%Y-%m-%d %H:%M:%S"
        return [time.strftime(format_str, time.gmtime(t)) for t in ts]

    def __repr__(self):
        return str(self)

    def __str__(self):
        l = "; ".join("{1} - {2} ({0})".format(w, *self.timestamps_to_str(p)) for p, w in self)
        return "[{}]".format(l)

    def __len__(self):
        return len(self.weights)

    def serialize(self):
        return map(list, (self.edges, self.weights))

    @classmethod
    def deserialize(cls, deviation, data):
        return WeightSegments(deviation, data[0], data[1])

    def add(self, value):
        self.add_range(*value[0], weight=value[1])

    @staticmethod
    def utctimestamp(dt):
        import calendar
        return calendar.timegm(dt.utctimetuple())

    def add_range(self, start, finish, weight=1):
        """
        Add segment

        :param start: Left edge of segment
        :param finish: Right edge of segment
        :param weight: Weight of segment
        """
        assert start <= finish
        if isinstance(start, datetime.datetime):
            start = self.utctimestamp(start)
        if isinstance(finish, datetime.datetime):
            finish = self.utctimestamp(finish)

        if not self.edges:
            # This segment is the first. Just add it
            self.edges = [start, finish]
            self.weights = [weight]
            return

        i = bisect.bisect_left(self.edges, start)  # index in edges array of min point
                                                   # which is greater than left edge of new segment
        j = bisect.bisect_right(self.edges, finish)  # index in edges array of max point
                                                     # which is less than right edge of new segment

        #
        #                   [------------]------[--]------------------[------]
        # edges:            1           10      13 15                 20     25
        # weights:                5               3                      7
        #                            ^                         ^
        # new segment:               |-------------------------|
        #                            7                         17
        #                                ^                            ^
        #                                i                            j

        start_inside = i % 2 == 1  # true if left edge is inside of any interval
        finish_inside = j % 2 == 1  # true if right edge is inside of any interval

        if start_inside:
            if self.edges[i] > finish:  # new segment is inside already existed segment
                #  -----[----------------------------------------------------------------]---
                #       ^                        ^                  ^                    ^
                #   edge[i-1]                  start              finish                edge[i]
                #
                # split to three segment:
                #
                #  -----[------------------------]---[--------------]---[----------------]---
                #       ^                        ^   ^              ^   ^                ^
                #   edge[i-1]              start-1   start     finish   finish+1        edge[i]
                #
                self.edges[i+1:i+1] = [finish+1, self.edges[i]]  # add third segment
                self.weights.insert(i//2, self.weights[i//2])  # add weight for new segment
                finish_inside = False

            # in the case when right edge of new segment just split to two segments:
            #  -----[---------------------------------]----------------------------------
            #       ^                        ^        ^                ^
            #   edge[i-1]                  start    edge[i]          finish
            #
            #  -----[------------------------]---[---------------------]-----------------
            #       ^                        ^   ^                     ^
            #   edge[i-1]              start-1   start               finish
            #
            self.edges[i] = start - 1  # correct right edge of existed segment (first segment on the image)
            i += 1

        self.edges[i:i] = [start, finish]  # insert new segment
        self.weights.insert(i//2, weight)  # insert weight for new segment
        j += 2  # segment were added therefore index for right edge is increased

        if finish_inside:
            # if the right edge of new segment is inside existed segments
            # then change left edge of next segment to finish + 1 (because weight can be different)
            self.edges[j-1] = finish+1
            j -= 1

        if i+2 < j:
            # remove segments which are covered by new segments
            del self.edges[i+2:j]
            del self.weights[i//2+1:j//2]

        # during splitting segments/adding new segment it is possible that neighbor segments can have
        # the same weight. In this case we can merge it.
        if i > 0:
            if self.edges[i] - self.edges[i-1] <= self.deviation and self.weights[i//2-1] == self.weights[i//2]:
                del self.weights[i//2]
                del self.edges[i-1:i+1]
                i -= 2

        if i+2 < len(self.edges):
            if self.edges[i+2] - self.edges[i+1] <= self.deviation and self.weights[i//2] == self.weights[i//2+1]:
                del self.weights[i//2+1]
                del self.edges[i+1:i+3]
        assert len(self.edges) == len(self.weights)*2

    def __iter__(self):
        return zip(grouped(self.edges, 2), self.weights)

    def in_range(self, start, end):
        edges = []
        weight = []
        for (s, e), w in self:
            s = max(s, start)
            e = min(e, end)
            if s < e:
                edges.append(s)
                edges.append(e)
                weight.append(w)
        return WeightSegments(self.deviation, edges, weight)

    def length(self):
        return sum((f - s + 1) for s, f in grouped(self.edges, 2))

    def weight(self):
        return sum((f - s + 1)*w for (s, f), w in self)

    def heaviest(self):
        return max(self.weights)

    def serialize_str(self):
        return ";".join("{1}-{2}|{0}".format(w, *self.timestamps_to_str(ts, short=True)) for ts, w in self)

    # 19700101 00:00:30-19700101 00:00:41|1
    r_serialize = re.compile(r"(\d{8} \d\d:\d\d:\d\d)-(\d{8} \d\d:\d\d:\d\d)\|(\d+)")

    @classmethod
    def str_to_timestamp(cls, s):
        try:
            return timegm(time.strptime(s, cls.serialize_time_format))
        except ValueError as e:
            logbook.error("Incorrect format of time string: {}: %s".format(s), e)
            return None

    @classmethod
    def deserialize_str(cls, s, deviation):
        result = cls(deviation)
        for segment in s.split(";"):
            m = re.match(cls.r_serialize, segment)
            if not m:
                logbook.error("Invalid time range string: {}".format(segment))
            else:
                start, finish, quantity = m.groups()
                start = cls.str_to_timestamp(start)
                finish = cls.str_to_timestamp(finish)
                if not start or not finish:
                    continue  # skip incorrect time
                quantity = int(quantity)
                result.add_range(start, finish, quantity)
        return result

    def merge(self, other):
        for i in other:
            self.add(i)

    def total_weight(self):
        return sum(self.weights)
