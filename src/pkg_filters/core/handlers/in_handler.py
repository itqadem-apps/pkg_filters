from __future__ import annotations

from typing import Any, Generic, Sequence, TypeVar

from ..pipeline import QueryContext, BaseQuerySpec

S = TypeVar("S")  # statement/builder type (Select, Search, list, etc.)
Q = TypeVar("Q", bound=BaseQuerySpec[Any, Any])
T = TypeVar("T")  # scalar type (enum, str, UUID, int, ...)


class BaseInFilterHandler(Generic[S, Q, T]):
    """
    Generic handler that integrates an "IN" filter into the query pipeline.

    Responsibilities:
    - Read a sequence of values from `ctx.spec.filters.<filter_attr>`.
    - If non-empty, run:

        values = get_values(ctx)
        stmt = prepare_stmt(stmt, ctx, values)
        stmt = apply_to_stmt(stmt, ctx, values)
        stmt = finalize_stmt(stmt, ctx, values)

    Designed to satisfy PipelineFilter[S, Q] by duck-typing.
    """

    skip_on_count: bool = False

    def __init__(self, filter_attr: str) -> None:
        """
        :param filter_attr: name of the attribute on `filters` that holds the sequence.
                            Example: "status_in" or "category_ids".
        """
        self._filter_attr = filter_attr

    # ---------- Pipeline entry ----------

    def apply(self, ctx: QueryContext[S, Q]) -> QueryContext[S, Q]:
        values = self.get_values(ctx)
        if not values:
            return ctx

        stmt = ctx.stmt
        stmt = self.prepare_stmt(stmt, ctx, values)
        stmt = self.apply_to_stmt(stmt, ctx, values)
        stmt = self.finalize_stmt(stmt, ctx, values)

        ctx.stmt = stmt
        return ctx

    # ---------- Hooks ----------

    def get_values(self, ctx: QueryContext[S, Q]) -> Sequence[T] | None:
        """
        Default: ctx.spec.filters.<filter_attr> as a sequence.

        Override if needed (e.g. transform set/tuple/etc).
        """
        filters = getattr(ctx.spec, "filters", None)
        if filters is None:
            return None
        seq = getattr(filters, self._filter_attr, None)
        if not seq:
            return None
        # ensure something indexable; you can also normalize to tuple(...)
        return seq

    def prepare_stmt(self, stmt: S, ctx: QueryContext[S, Q], values: Sequence[T]) -> S:
        """
        Hook before applying IN condition.
        Typical use:
        - joins

        Default: no-op.
        """
        return stmt

    def apply_to_stmt(self, stmt: S, ctx: QueryContext[S, Q], values: Sequence[T]) -> S:
        """
        Must be implemented by persistence-specific adapter.
        """
        raise NotImplementedError

    def finalize_stmt(self, stmt: S, ctx: QueryContext[S, Q], values: Sequence[T]) -> S:
        """
        Hook after applying IN condition (loader options, etc).

        Default: no-op.
        """
        return stmt
