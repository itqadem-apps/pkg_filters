from __future__ import annotations

from typing import Any, Generic, TypeVar

from ..pipeline import BaseQuerySpec, QueryContext
from ..specs import RangeFilterVO

S = TypeVar("S")  # statement/builder type (Select, ES query, etc.)
Q = TypeVar("Q", bound=BaseQuerySpec[Any, Any])
T = TypeVar("T")  # “scalar” type inside the range (int, Decimal, datetime, ...)


class BaseRangeFilterHandler(Generic[S, Q, T]):
    """
    Generic handler that integrates a RangeFilter[T] into the query pipeline.

    Responsibilities:
    - Read a RangeFilter[T] from `ctx.spec.filters.<filter_attr>`.
    - If not empty, run a small hook pipeline:

        rf = get_range(ctx)
        stmt = prepare_stmt(stmt, ctx, rf)
        stmt = apply_to_stmt(stmt, ctx, rf)
        stmt = finalize_stmt(stmt, ctx, rf)

    Designed to satisfy the PipelineFilter[S, Q] protocol (duck-typed).
    """

    skip_on_count: bool = False  # usually we *do* want ranges in COUNT

    def __init__(self, filter_attr: str) -> None:
        """
        :param filter_attr: attribute name on `filters` where the RangeFilter[T] lives.
                            Example: "price" or "number_of_chapters".
        """
        self._filter_attr = filter_attr

    # -------- Public entry (called by Pipeline) --------

    def apply(self, ctx: QueryContext[S, Q]) -> QueryContext[S, Q]:
        rf = self.get_range(ctx)
        if rf is None or rf.is_empty():
            return ctx

        stmt = ctx.stmt
        stmt = self.prepare_stmt(stmt, ctx, rf)
        stmt = self.apply_to_stmt(stmt, ctx, rf)
        stmt = self.finalize_stmt(stmt, ctx, rf)

        ctx.stmt = stmt
        return ctx

    # -------- Hooks you can override in subclasses --------

    def get_range(self, ctx: QueryContext[S, Q]) -> RangeFilterVO[T] | None:
        """
        Hook to read the RangeFilter[T] from the context.

        Default: `ctx.spec.filters.<filter_attr>` if present.
        Override if you have a more complex location or dynamic logic.
        """
        filters = getattr(ctx.spec, "filters", None)
        if filters is None:
            return None
        return getattr(filters, self._filter_attr, None)

    def prepare_stmt(self, stmt: S, ctx: QueryContext[S, Q], rf: RangeFilterVO[T]) -> S:
        """
        Hook for pre-processing the statement before applying conditions.

        Typical use:
        - Add joins for related tables (SQLAlchemy).
        - Add base predicates.

        Default: no-op.
        """
        return stmt

    def apply_to_stmt(self, stmt: S, ctx: QueryContext[S, Q], rf: RangeFilterVO[T]) -> S:
        """
        Core hook: apply the range constraints to the statement.

        This is usually where you add `where` / `filter` calls, etc.

        Must be implemented by subclasses.
        """
        raise NotImplementedError

    def finalize_stmt(self, stmt: S, ctx: QueryContext[S, Q], rf: RangeFilterVO[T]) -> S:
        """
        Hook for post-processing the statement.

        Typical use:
        - Add `options(selectinload(...))` or `options(joinedload(...))`.
        - Add ordering that depends on the range.

        Default: no-op.
        """
        return stmt
