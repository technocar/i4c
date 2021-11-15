from datetime import datetime
from typing import Optional, List


class TimePeriod:
    """ representing an [start, end) intervall """
    __slots__ = ['start', 'end']
    start: Optional[datetime]
    end: Optional[datetime]

    def __init__(self, start:Optional[datetime] = None, end:Optional[datetime] = None):
        self.start = start
        self.end = end

    def __str__(self):
        return f"{self.start} - {self.end}"

    def is_timestamp_in(self, p: Optional[datetime]):
        """ p = None => p = -inf """
        if self.start is not None:
            if p is None or (self.start > p):
                return False
        if self.end is not None:
            if p is not None and (self.end <= p):
                return False
        return True


class Series:
    __slots__ = ['_items']
    _items: List[TimePeriod]

    def __init__(self):
        self._items = []  # disjunct TimePeriod items, ordered by start

    def __str__(self):
        return ",\n".join(f"{idx}.   {i}" for idx, i in enumerate(self._items, start=1))

    def add(self, tnew:TimePeriod):

        def logsearch_first(a, f):
            min = 0
            max = len(a) - 1
            res = len(a)
            while min <= max:
                m = (min + max) // 2
                if f(a, m):
                    max = m - 1
                    res = m
                else:
                    min = m + 1
            return res

        def f(a, idx):
            return (a[idx].end is None
                    or tnew.start is None
                    or (a[idx].end >= tnew.start))

        idx = logsearch_first(self._items, f)
        while idx < len(self._items):
            item = self._items[idx]

            if item.start > tnew.end:
                break

            if tnew.start is not None:
                if item.start is None or (item.start < tnew.start):
                    tnew.start = item.start
            if tnew.end is not None:
                if item.end is None or (item.end > tnew.end):
                    tnew.end = item.end
            del self._items[idx]

        self._items.insert(idx, tnew)

    @staticmethod
    def intersect(s1, s2):
        """
        :type s1: Series
        :type s2: Series
        :rtype Series
        """
        res = Series()
        if len(s1._items) == 0 or len(s2._items) == 0:
            return res

        i1, i2 = 0,0
        item1 = s1._items[i1]  # type: TimePeriod
        item2 = s2._items[i2]  # type: TimePeriod

        p = None if item1.start is None and item2.start is None else \
            item1.start if item2.start is None else \
            item2.start if item1.start is None else \
            max(item1.start, item2.start)

        intervall_start = None
        intervall_started = False
        while True:
            item1 = s1._items[i1]  # type: TimePeriod
            item2 = s2._items[i2]  # type: TimePeriod

            if item1.is_timestamp_in(p) and item2.is_timestamp_in(p):
                if not intervall_started:
                    intervall_started = True
                    intervall_start = p
            else:
                if intervall_started:
                    res._items.append(TimePeriod(intervall_start, p))
                    intervall_started = False

            if item1.end == p:
                i1 += 1
            if item2.end == p:
                i2 += 1

            if i1 == len(s1._items):
                break
            if i2 == len(s2._items):
                break

            item1 = s1._items[i1]  # type: TimePeriod
            item2 = s2._items[i2]  # type: TimePeriod

            p = min(i for i in (item1.start, item1.end, item2.start, item2.end) if i is not None and (p is None or i > p))

        if intervall_started:
            res._items.append(TimePeriod(intervall_start, None))
        return res
