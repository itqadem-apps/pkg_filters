from __future__ import annotations

from typing import Any, Callable, Generic, Iterable, TypeVar

from sqlalchemy.sql import Select

from ....core import QueryContext, BaseQuerySpec, BaseExactFilterHandler

Q = TypeVar("Q", bound=BaseQuerySpec[Any, Any])
T = TypeVar("T")

ExactJoinFn = Callable[[Select, QueryContext[Select, Q], T], Select]
ExactLoadOptionsFactory = Callable[[QueryContext[Select, Q], T], Iterable[Any]]
ExactPredicateFactory = Callable[[QueryContext[Select, Q], T], Any]


class SqlAlchemyExactFilter(BaseExactFilterHandler[Select, Q, T], Generic[Q, T]):
    """
    SQLAlchemy adapter for exact (column == value) filters.

    Supports two modes:

    1) Simple column-based:
        - column: SQLAlchemy column/expression
        -> condition: column == value (or customizable)

    2) Custom predicate:
        - predicate_factory: (ctx, value) -> SQLA boolean expression

    Plus:
      - join_fn              : optional joins
      - load_options_factory : optional loader options (data queries only)
    """

    def __init__(
        self,
        filter_attr: str,
        *,
        column: Any | None = None,
        join_fn: ExactJoinFn | None = None,
        load_options_factory: ExactLoadOptionsFactory | None = None,
        predicate_factory: ExactPredicateFactory | None = None,
    ) -> None:
        super().__init__(filter_attr)
        self._column = column
        self._join_fn = join_fn
        self._load_options_factory = load_options_factory
        self._predicate_factory = predicate_factory

    # ---------- Hooks from BaseExactFilterHandler ----------

    def prepare_stmt(
        self,
        stmt: Select,
        ctx: QueryContext[Select, Q],
        value: T,
    ) -> Select:
        if self._join_fn is not None:
            stmt = self._join_fn(stmt, ctx, value)
        return stmt

    def apply_to_stmt(
        self,
        stmt: Select,
        ctx: QueryContext[Select, Q],
        value: T,
    ) -> Select:
        expr = self.build_predicate(ctx, value)
        if expr is None:
            return stmt
        return stmt.where(expr)

    def finalize_stmt(
        self,
        stmt: Select,
        ctx: QueryContext[Select, Q],
        value: T,
    ) -> Select:
        # 🔴 IMPORTANT: skip loader options on count queries
        if ctx.for_count or self._load_options_factory is None:
            return stmt

        options = list(self._load_options_factory(ctx, value))
        if not options:
            return stmt
        return stmt.options(*options)

    # ---------- Extra helper ----------

    def build_predicate(
        self,
        ctx: QueryContext[Select, Q],
        value: T,
    ) -> Any:
        if self._predicate_factory is not None:
            return self._predicate_factory(ctx, value)

        if self._column is None:
            raise RuntimeError(
                "SqlAlchemyExactFilter: either `column` or `predicate_factory` must be provided."
            )

        # default equality: suitable for enums, strings, UUIDs, etc.
        return self._column == value
