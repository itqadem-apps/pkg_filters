from __future__ import annotations

from typing import Any, Generic, TypeVar

from ..pipeline import BaseQuerySpec, QueryContext

S = TypeVar("S")  # statement/builder type (Select, Search, list, etc.)
Q = TypeVar("Q", bound=BaseQuerySpec[Any, Any])
T = TypeVar("T")  # scalar type (enum, str, UUID, int, ...)


class BaseExactFilterHandler(Generic[S, Q, T]):
    """
    Generic handler that integrates an exact-match filter into the query pipeline.

    Responsibilities:
    - Read a value from `ctx.spec.filters.<filter_attr>`.
    - If not None, run:

        value = get_value(ctx)
        stmt = prepare_stmt(stmt, ctx, value)
        stmt = apply_to_stmt(stmt, ctx, value)
        stmt = finalize_stmt(stmt, ctx, value)

    Designed to satisfy PipelineFilter[S, Q] by duck-typing.
    """

    skip_on_count: bool = False  # usually we want exact filters in COUNT too

    def __init__(self, filter_attr: str) -> None:
        """
        :param filter_attr: name of the attribute on `filters` that holds the value.
                            Example: "status" or "category".
        """
        self._filter_attr = filter_attr

    # ---------- Pipeline entry ----------

    def apply(self, ctx: QueryContext[S, Q]) -> QueryContext[S, Q]:
        value = self.get_value(ctx)
        if value is None:
            return ctx

        stmt = ctx.stmt
        stmt = self.prepare_stmt(stmt, ctx, value)
        stmt = self.apply_to_stmt(stmt, ctx, value)
        stmt = self.finalize_stmt(stmt, ctx, value)

        ctx.stmt = stmt
        return ctx

    # ---------- Hooks ----------

    def get_value(self, ctx: QueryContext[S, Q]) -> T | None:
        """
        Default: ctx.spec.filters.<filter_attr>.
        Override for more complex logic.
        """
        filters = getattr(ctx.spec, "filters", None)
        if filters is None:
            return None
        return getattr(filters, self._filter_attr, None)

    def prepare_stmt(self, stmt: S, ctx: QueryContext[S, Q], value: T) -> S:
        """
        Hook before applying the exact condition.
        Typical use:
        - joins
        - base predicates

        Default: no-op.
        """
        return stmt

    def apply_to_stmt(self, stmt: S, ctx: QueryContext[S, Q], value: T) -> S:
        """
        Must be implemented by persistence-specific adapter.
        """
        raise NotImplementedError

    def finalize_stmt(self, stmt: S, ctx: QueryContext[S, Q], value: T) -> S:
        """
        Hook after applying the condition.
        Typical use:
        - loader options: selectinload / joinedload
        - order by

        Default: no-op.
        """
        return stmt
