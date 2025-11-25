from __future__ import annotations

from typing import Any, Callable, Generic, Iterable, Sequence, TypeVar

from sqlalchemy import not_
from sqlalchemy.sql import Select

from ....core import BaseQuerySpec, QueryContext,  BaseInFilterHandler

Q = TypeVar("Q", bound=BaseQuerySpec[Any, Any])
T = TypeVar("T")

InJoinFn = Callable[[Select, QueryContext[Select, Q], Sequence[T]], Select]
InLoadOptionsFactory = Callable[[QueryContext[Select, Q], Sequence[T]], Iterable[Any]]
InPredicateFactory = Callable[[QueryContext[Select, Q], Sequence[T]], Any]


class SqlAlchemyInFilter(BaseInFilterHandler[Select, Q, T], Generic[Q, T]):
    """
    SQLAlchemy adapter for IN filters.

    Modes:

    1) Simple column-based:
        - column: SQLAlchemy column/expression
        -> WHERE column IN (:values)

    2) Custom predicate:
        - predicate_factory: (ctx, values) -> expression

    Plus:
      - join_fn              : optional joins
      - load_options_factory : optional loader options
    """

    def __init__(
            self,
            filter_attr: str,
            *,
            column: Any | None = None,
            join_fn: InJoinFn[Q, T] | None = None,
            load_options_factory: InLoadOptionsFactory[Q, T] | None = None,
            predicate_factory: InPredicateFactory[Q, T] | None = None,
    ) -> None:
        super().__init__(filter_attr)
        self._column = column
        self._join_fn = join_fn
        self._load_options_factory = load_options_factory
        self._predicate_factory = predicate_factory

    # ---------- Hooks from BaseInFilterHandler ----------

    def prepare_stmt(
            self,
            stmt: Select,
            ctx: QueryContext[Select, Q],
            values: Sequence[T],
    ) -> Select:
        if self._join_fn is not None:
            stmt = self._join_fn(stmt, ctx, values)
        return stmt

    def apply_to_stmt(
            self,
            stmt: Select,
            ctx: QueryContext[Select, Q],
            values: Sequence[T],
    ) -> Select:
        expr = self.build_predicate(ctx, values)
        if expr is None:
            return stmt
        return stmt.where(expr)

    def finalize_stmt(
            self,
            stmt: Select,
            ctx: QueryContext[Select, Q],
            values: Sequence[T],
    ) -> Select:
        if ctx.for_count or self._load_options_factory is None:
            return stmt

        options = list(self._load_options_factory(ctx, values))
        if not options:
            return stmt

        return stmt.options(*options)

    # ---------- Extra helper ----------

    def build_predicate(
            self,
            ctx: QueryContext[Select, Q],
            values: Sequence[T],
    ) -> Any:
        if self._predicate_factory is not None:
            return self._predicate_factory(ctx, values)

        if self._column is None:
            raise RuntimeError(
                "SqlAlchemyInFilter: either `column` or `predicate_factory` must be provided."
            )

        # standard IN(...). works for enums, UUIDs, etc.
        return self._column.in_(list(values))


class SqlAlchemyNotInFilter(SqlAlchemyInFilter[Q, T], Generic[Q, T]):
    """
    NOT-IN variant of SqlAlchemyInFilter.

    It shares everything with SqlAlchemyInFilter (filter_attr, column, join_fn,
    load_options_factory, predicate_factory) but negates the predicate:

        IN-filter:     column IN (:values)
        NOT-IN-filter: NOT(column IN (:values))

    or, if you provide a predicate_factory, it will wrap that in NOT(...).
    """

    def build_predicate(
            self,
            ctx: QueryContext[Select, Q],
            values: Sequence[T],
    ) -> Any:
        # Use the normal IN predicate from parent...
        in_expr = super().build_predicate(ctx, values)
        # ...and simply negate it.
        return not_(in_expr)
