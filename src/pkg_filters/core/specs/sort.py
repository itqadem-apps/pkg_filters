from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Sequence, Literal

SortDirection = Literal["asc", "desc"]
NullsPosition = Literal["first", "last"]


@dataclass(frozen=True)
class SortField:
    """
    Single sort field description.

    - field:      logical field name (e.g. "created_at", "title", "price")
    - direction:  "asc" or "desc"
    - nulls:      optional null handling ("first" / "last") if supported by backend
    """
    field: str
    direction: SortDirection = "asc"
    nulls: NullsPosition | None = None


@dataclass(frozen=True)
class SortSpec:
    """
    A list of fields to sort by, in order of priority.
    """
    fields: Sequence[SortField] = dc_field(default_factory=tuple)

    def is_empty(self) -> bool:
        return not self.fields
