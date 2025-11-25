# infra/sqlalchemy/sort_filter.py
from __future__ import annotations

from typing import Any, Callable, Dict, Generic, TypeVar

from sqlalchemy.sql import Select

from ....core import BaseQuerySpec, QueryContext
from ....core.specs import SortField, SortSpec

Q = TypeVar("Q", bound=BaseQuerySpec[Any, Any])

# Sort handler: (stmt, ctx, sort_field) -> stmt
SortHandler = Callable[[Select, QueryContext[Select, Q], SortField], Select]


class SqlAlchemySortFilter(Generic[Q]):
    """
    Simple, reliable sorting filter.

    - Reads `ctx.spec.sort`.
    - For each SortField:
        1) If field in `sort_map`, call its handler.
        2) Else, fallback: ORDER BY <orm_model.field> ASC/DESC.

    This class matches your PipelineFilter protocol (skip_on_count + apply).
    """

    skip_on_count: bool = True  # we don't sort COUNT queries

    def __init__(
            self,
            orm_model: Any,
            sort_map: Dict[str, SortHandler[Q]] | None = None,
    ) -> None:
        self._model = orm_model
        self._sort_map: Dict[str, SortHandler[Q]] = sort_map or {}

    def apply(self, ctx: QueryContext[Select, Q]) -> QueryContext[Select, Q]:
        spec_sort: SortSpec | None = getattr(ctx.spec, "sort", None)
        if spec_sort is None or spec_sort.is_empty():
            return ctx

        stmt = ctx.stmt

        for sf in spec_sort.fields:
            handler = self._sort_map.get(sf.field)
            if handler is not None:
                # Custom handler can join, compute expression, etc.
                stmt = handler(stmt, ctx, sf)
            else:
                # Fallback: direct column on root ORM model
                stmt = self._apply_default_sort(stmt, sf)

        ctx.stmt = stmt
        return ctx

    # -------- Fallback sorting --------

    def _apply_default_sort(self, stmt: Select, sf: SortField) -> Select:
        if not hasattr(self._model, sf.field):
            raise KeyError(
                f"SqlAlchemySortFilter: no custom handler for sort field {sf.field!r} "
                f"and {self._model.__name__} has no such attribute"
            )

        col = getattr(self._model, sf.field)
        expr = col.asc() if sf.direction == "asc" else col.desc()
        return stmt.order_by(expr)
