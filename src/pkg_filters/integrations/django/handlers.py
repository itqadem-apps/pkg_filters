from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence, TypeVar

from django.db.models import F, Q as DjangoQ, QuerySet

from ...core import (
    BaseBoolFilterHandler,
    BaseExactFilterHandler,
    BaseInFilterHandler,
    BaseQuerySpec,
    BaseRangeFilterHandler,
    BaseSortHandler,
    RangeFilterVO,
    SortField,
    SortSpec,
)
from ...core.pipeline import QueryContext

QSpec = TypeVar("QSpec", bound=BaseQuerySpec[Any, Any])


@dataclass(frozen=True)
class SortMapValue:
    """
    How a logical sort field maps to Django ORM.

    - expr: field name (e.g. "created_at") or an F-expression key understood by F(...)
    - allow_nulls: if True, apply SortField.nulls when provided (requires Django DB support)
    """

    expr: str
    allow_nulls: bool = True


class DjangoExactFilterHandler(BaseExactFilterHandler[QuerySet, QSpec, Any]):
    def __init__(
        self,
        filter_attr: str,
        *,
        lookup: str | None = None,
        transform: Callable[[Any], Any] | None = None,
    ) -> None:
        super().__init__(filter_attr)
        self._lookup = lookup or filter_attr
        self._transform = transform

    def apply_to_stmt(self, stmt: QuerySet, ctx: QueryContext[QuerySet, QSpec], value: Any) -> QuerySet:
        if self._transform is not None:
            value = self._transform(value)
        return stmt.filter(**{self._lookup: value})


class DjangoInFilterHandler(BaseInFilterHandler[QuerySet, QSpec, Any]):
    def __init__(
        self,
        filter_attr: str,
        *,
        lookup: str | None = None,
        transform: Callable[[Any], Any] | None = None,
    ) -> None:
        super().__init__(filter_attr)
        self._lookup = lookup or f"{filter_attr}__in"
        self._transform = transform

    def apply_to_stmt(
        self,
        stmt: QuerySet,
        ctx: QueryContext[QuerySet, QSpec],
        values: Sequence[Any],
    ) -> QuerySet:
        if self._transform is not None:
            values = [self._transform(v) for v in values]
        return stmt.filter(**{self._lookup: values})


class DjangoBoolFilterHandler(BaseBoolFilterHandler[QuerySet, QSpec]):
    def __init__(self, filter_attr: str, *, lookup: str | None = None) -> None:
        super().__init__(filter_attr)
        self._lookup = lookup or filter_attr

    def apply_to_stmt(self, stmt: QuerySet, ctx: QueryContext[QuerySet, QSpec], value: bool) -> QuerySet:
        return stmt.filter(**{self._lookup: value})


class DjangoRangeFilterHandler(BaseRangeFilterHandler[QuerySet, QSpec, Any]):
    def __init__(self, filter_attr: str, *, field: str | None = None) -> None:
        super().__init__(filter_attr)
        self._field = field or filter_attr

    def apply_to_stmt(
        self,
        stmt: QuerySet,
        ctx: QueryContext[QuerySet, QSpec],
        rf: RangeFilterVO[Any],
    ) -> QuerySet:
        lookups: dict[str, Any] = {}
        if rf.eq is not None:
            lookups[self._field] = rf.eq
        if rf.gt is not None:
            lookups[f"{self._field}__gt"] = rf.gt
        if rf.gte is not None:
            lookups[f"{self._field}__gte"] = rf.gte
        if rf.lt is not None:
            lookups[f"{self._field}__lt"] = rf.lt
        if rf.lte is not None:
            lookups[f"{self._field}__lte"] = rf.lte
        return stmt.filter(**lookups)


class DjangoSearchFilterHandler(DjangoExactFilterHandler):
    """
    OR search across multiple text fields using `icontains`.

    Reads the search term from `ctx.spec.filters.<filter_attr>`.
    """

    def __init__(
        self,
        filter_attr: str,
        *,
        fields: Sequence[str],
        min_len: int = 1,
    ) -> None:
        super().__init__(filter_attr)
        self._fields = tuple(fields)
        self._min_len = min_len

    def apply_to_stmt(self, stmt: QuerySet, ctx: QueryContext[QuerySet, QSpec], value: Any) -> QuerySet:
        if value is None:
            return stmt
        term = str(value).strip()
        if len(term) < self._min_len:
            return stmt

        query = DjangoQ()
        for field_name in self._fields:
            query |= DjangoQ(**{f"{field_name}__icontains": term})

        return stmt.filter(query)


class DjangoSortHandler(BaseSortHandler[QuerySet, QSpec]):
    """
    Sort adapter for Django QuerySet.

    Provide a `sort_map` to translate logical sort fields to ORM fields/expressions.
    If a key is missing, the logical name is used as a field name.
    """

    def __init__(
        self,
        *,
        sort_attr: str = "sort",
        sort_map: Mapping[str, str | SortMapValue] | None = None,
    ) -> None:
        super().__init__(sort_attr=sort_attr)
        self._sort_map = dict(sort_map or {})

    def apply_to_stmt(
        self,
        stmt: QuerySet,
        ctx: QueryContext[QuerySet, QSpec],
        sort_spec: SortSpec,
    ) -> QuerySet:
        order_by_args: list[Any] = []
        for sf in sort_spec.fields:
            order_by_args.append(self._to_order_by(sf))
        return stmt.order_by(*order_by_args)

    def _to_order_by(self, sf: SortField) -> Any:
        mapped = self._sort_map.get(sf.field, sf.field)

        if isinstance(mapped, SortMapValue):
            expr = mapped.expr
            allow_nulls = mapped.allow_nulls
        else:
            expr = mapped
            allow_nulls = True

        direction = sf.direction.lower()
        if direction not in ("asc", "desc"):
            raise ValueError(f"Invalid sort direction: {sf.direction!r}")

        if sf.nulls is None or not allow_nulls:
            return f"-{expr}" if direction == "desc" else expr

        fexpr = F(expr)
        nulls_position = sf.nulls.lower()
        if nulls_position not in ("first", "last"):
            raise ValueError(f"Invalid nulls position: {sf.nulls!r}")

        if direction == "asc":
            if nulls_position == "first":
                return fexpr.asc(nulls_first=True)
            return fexpr.asc(nulls_last=True)

        if nulls_position == "first":
            return fexpr.desc(nulls_first=True)
        return fexpr.desc(nulls_last=True)

class DjangoAllExactFiltersHandler:
    def __init__(self, *, excluded: set[str] | None = None) -> None:
        self._excluded = excluded or set()

    def apply(self, ctx: DjangoQueryContext) -> DjangoQueryContext:
        filters = getattr(ctx.spec, "filters", None)
        if filters is None:
            return ctx

        for field in dc_fields(filters):
            name = field.name
            if name in self._excluded:
                continue
            value = getattr(filters, name, None)
            if value is None:
                continue
            ctx.stmt = ctx.stmt.filter(**{name: value})

        return ctx