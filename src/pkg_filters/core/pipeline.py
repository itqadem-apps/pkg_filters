from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, TypeVar, Generic, Any, Protocol, Sequence

from .specs import BaseQuerySpec

Q = TypeVar("Q", bound=BaseQuerySpec[Any, Any])
S = TypeVar("S")  # The "statement"/"builder" type (Select, Search, list, etc.)


@dataclass
class QueryContext(Generic[S, Q]):
    """
    Generic query context that the pipeline mutates.

    - stmt: any query/builder object (SQLAlchemy Select, Elastic Search, etc.)
    - spec: any BaseQuerySpec subclass
    - for_count: toggle for COUNT queries
    """
    stmt: S
    spec: Q
    for_count: bool = False
    state: dict[str, Any] = field(default_factory=dict)

    def get_or_set(self, key: str, value_factory: Callable[[], Any]) -> Any:
        if key in self.state:
            return self.state[key]
        value = value_factory()
        self.state[key] = value
        return value



class PipelineFilter(Protocol[S, Q]):
    """
    Base pipeline filter protocol.

    Works with any QueryContext whose .spec is a BaseQuerySpec subclass
    and whose .stmt is S (SQLAlchemy Select, ES query, etc.).
    """

    skip_on_count: bool

    def apply(self, ctx: QueryContext[S, Q]) -> QueryContext[S, Q]:
        ...


class Pipeline(Generic[S, Q]):
    """
    Generic query pipeline that runs a sequence of PipelineFilter[S, Q]
    over a QueryContext[S, Q].
    """

    def __init__(self, filters: Sequence[PipelineFilter[S, Q]]):
        self._filters = list(filters)

    def run(self, ctx: QueryContext[S, Q]) -> QueryContext[S, Q]:
        for f in self._filters:
            if getattr(f, "skip_on_count", False) and ctx.for_count:
                continue
            ctx = f.apply(ctx)
        return ctx
