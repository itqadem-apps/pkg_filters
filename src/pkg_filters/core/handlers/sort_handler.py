# core/query/sort_handler.py
from __future__ import annotations

from typing import Any, Generic, TypeVar

from ..pipeline import QueryContext, BaseQuerySpec
from ..specs import SortSpec

S = TypeVar("S")  # statement / builder type (Select, ES query, etc.)
Q = TypeVar("Q", bound=BaseQuerySpec[Any, Any])


class BaseSortHandler(Generic[S, Q]):
    """
    Generic handler that integrates sorting into the query pipeline.

    - Reads a SortSpec from `ctx.spec.<sort_attr>` (default: ctx.spec.sort)
    - If non-empty, delegates to `apply_to_stmt`.

    Duck-typed to satisfy PipelineFilter[S, Q].
    """

    # Sorting is irrelevant for COUNT queries, so we skip by default.
    skip_on_count: bool = True

    def __init__(self, sort_attr: str = "sort") -> None:
        """
        :param sort_attr: attribute name on the spec where SortSpec is stored.
                          Example: "sort" or "order_by".
        """
        self._sort_attr = sort_attr

    # -------- Pipeline entry --------

    def apply(self, ctx: QueryContext[S, Q]) -> QueryContext[S, Q]:
        sort_spec: SortSpec | None = getattr(ctx.spec, self._sort_attr, None)
        if sort_spec is None or sort_spec.is_empty():
            return ctx

        stmt = ctx.stmt
        stmt = self.apply_to_stmt(stmt, ctx, sort_spec)
        ctx.stmt = stmt
        return ctx

    # -------- Hook for adapters --------

    def apply_to_stmt(
            self,
            stmt: S,
            ctx: QueryContext[S, Q],
            sort_spec: SortSpec,
    ) -> S:
        """
        Must be implemented by persistence-specific adapters.

        Example responsibilities:
        - translate logical field names to columns / expressions
        - build ORDER BY clauses
        """
        raise NotImplementedError
