from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, time
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RangeFilterVO(Generic[T]):
    """
    Persistence-agnostic range value object.

    You can express:
    - exact equality (eq)
    - open/closed intervals using gt/gte/lt/lte

    Example:
        RangeFilter(gte=10, lt=100)
    """
    eq: T | None = None
    gt: T | None = None
    gte: T | None = None
    lt: T | None = None
    lte: T | None = None

    def is_empty(self) -> bool:
        return all(
            v is None
            for v in (self.eq, self.gt, self.gte, self.lt, self.lte)
        )


DateTimeRangeFilterVO = RangeFilterVO[datetime]
DateRangeFilterVO = RangeFilterVO[date]
TimeRangeFilterVO = RangeFilterVO[time]
