# core/query/bool_handler.py
from __future__ import annotations

from typing import Any, Generic, TypeVar

from ..pipeline import QueryContext
from ..specs.base import BaseQuerySpec

S = TypeVar("S")  # statement/builder type (Select, Search, list, etc.)
Q = TypeVar("Q", bound=BaseQuerySpec[Any, Any])


class BaseBoolFilterHandler(Generic[S, Q]):
    """
    Generic handler that integrates a bool filter into the query pipeline.

    Responsibilities:
    - Read a bool from `ctx.spec.filters.<filter_attr>`.
    - If not None, run a hook pipeline:

        value = get_value(ctx)
        stmt = prepare_stmt(stmt, ctx, value)
        stmt = apply_to_stmt(stmt, ctx, value)
        stmt = finalize_stmt(stmt, ctx, value)

    Designed to satisfy the PipelineFilter[S, Q] protocol (duck-typed).
    """

    # Most of the time we *do* want boolean filters active on COUNT queries
    skip_on_count: bool = False

    def __init__(self, filter_attr: str) -> None:
        """
        :param filter_attr: attribute name on `filters` where the bool lives.
                            Example: "is_live" or "has_lessons".
        """
        self._filter_attr = filter_attr

    # -------- Public entry (called by Pipeline) --------

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

    # -------- Hooks for subclasses / adapters --------

    def get_value(self, ctx: QueryContext[S, Q]) -> bool | None:
        """
        Hook to read the bool value from the context.

        Default: `ctx.spec.filters.<filter_attr>` if present.
        Override if you need a more complex source.
        """
        filters = getattr(ctx.spec, "filters", None)
        if filters is None:
            return None
        return getattr(filters, self._filter_attr, None)

    def prepare_stmt(self, stmt: S, ctx: QueryContext[S, Q], value: bool) -> S:
        """
        Hook for pre-processing the statement before applying conditions.

        Typical use:
        - Add joins for related tables (SQLAlchemy).
        - Add base predicates.

        Default: no-op.
        """
        return stmt

    def apply_to_stmt(self, stmt: S, ctx: QueryContext[S, Q], value: bool) -> S:
        """
        Core hook: apply the boolean constraint to the statement.

        MUST be implemented by subclasses (e.g. SQLAlchemy, ES).
        """
        raise NotImplementedError

    def finalize_stmt(self, stmt: S, ctx: QueryContext[S, Q], value: bool) -> S:
        """
        Hook for post-processing the statement.

        Typical use:
        - Add `options(selectinload(...))` or `options(joinedload(...))`.
        - Add ordering that depends on the boolean.

        Default: no-op.
        """
        return stmt
