from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeVar, Set, Generic

from .sort import SortSpec

F = TypeVar("F")
P = TypeVar("P")


@dataclass(frozen=True)
class BaseProjectionSpec:
    """
    Minimal, generic projection spec.

    - scalar_fields: root-level scalar fields to fetch.
      Domain-specific projections can subclass this and add flags
      like include_translations, include_chapters, etc.
    """
    scalar_fields: Set[str] = field(default_factory=set)


@dataclass(frozen=True)
class BaseQuerySpec(Generic[F, P]):
    """
    Generic application-level description of a read query.

    This is completely persistence-agnostic:
    - limit / offset (or whatever paging you choose)
    - projection (P)
    - filter spec (F)
    - sort spec (SortSpec)
    """
    limit: int
    offset: int
    projection: P
    filters: F
    sort: SortSpec | None = None
