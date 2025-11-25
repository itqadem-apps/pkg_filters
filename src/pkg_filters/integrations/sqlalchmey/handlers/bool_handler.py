from __future__ import annotations

from typing import Any, Callable, Generic, Iterable, TypeVar

from sqlalchemy import not_
from sqlalchemy.sql import Select

from ....core import BaseQuerySpec, QueryContext, BaseBoolFilterHandler

Q = TypeVar("Q", bound=BaseQuerySpec[Any, Any])

# Callbacks for customization
BoolJoinFn = Callable[[Select, QueryContext[Select, Q], bool], Select]
BoolLoadOptionsFactory = Callable[[QueryContext[Select, Q], bool], Iterable[Any]]
BoolPredicateFactory = Callable[[QueryContext[Select, Q], bool], Any]


class SqlAlchemyBoolFilter(BaseBoolFilterHandler[Select, Q], Generic[Q]):
    """
    SQLAlchemy adapter for boolean filters.

    You can configure it in two main ways:

    1) Simple column-based:
        - column: SQLAlchemy column (bool-type or truthy expression)
        -> value=True  => WHERE column IS TRUE (or column == True)
           value=False => WHERE column IS FALSE (or NOT column)

    2) Fully custom predicate:
        - predicate_factory: (ctx, value) -> SQLAlchemy boolean expression
        -> you handle True/False however you want.

    Additionally:
      - join_fn              : optional function to apply joins
      - load_options_factory : optional factory for loader options (selectinload, joinedload, ...)
    """

    def __init__(
            self,
            filter_attr: str,
            *,
            column: Any | None = None,
            join_fn: BoolJoinFn[Q] | None = None,
            load_options_factory: BoolLoadOptionsFactory[Q] | None = None,
            predicate_factory: BoolPredicateFactory[Q] | None = None,
            use_is_: bool = True,
    ) -> None:
        """
        :param filter_attr: attribute name on `filters` where the bool lives.
        :param column: bool or bool-like SQLAlchemy column/expression (for simple mode).
        :param join_fn: optional function (stmt, ctx, value) -> stmt that performs joins.
        :param load_options_factory: optional factory producing loader options for .options().
        :param predicate_factory: optional custom predicate builder (ctx, value) -> expression.
                                  Takes precedence over `column` if provided.
        :param use_is_: if True, use `column.is_(True/False)`, otherwise `column == value`
                        in simple column mode.
        """
        super().__init__(filter_attr)
        self._column = column
        self._join_fn = join_fn
        self._load_options_factory = load_options_factory
        self._predicate_factory = predicate_factory
        self._use_is = use_is_

    # -------- Hooks from BaseBoolFilterHandler --------

    def prepare_stmt(
            self,
            stmt: Select,
            ctx: QueryContext[Select, Q],
            value: bool,
    ) -> Select:
        if self._join_fn is not None:
            stmt = self._join_fn(stmt, ctx, value)
        return stmt

    def apply_to_stmt(
            self,
            stmt: Select,
            ctx: QueryContext[Select, Q],
            value: bool,
    ) -> Select:
        expr = self.build_predicate(ctx, value)
        if expr is None:
            return stmt
        return stmt.where(expr)

    def finalize_stmt(
            self,
            stmt: Select,
            ctx: QueryContext[Select, Q],
            value: bool,
    ) -> Select:
        if ctx.for_count or self._load_options_factory is None:
            return stmt

        options = list(self._load_options_factory(ctx, value))
        if not options:
            return stmt

        return stmt.options(*options)

    # -------- Extra helpers / hooks --------

    def build_predicate(
            self,
            ctx: QueryContext[Select, Q],
            value: bool,
    ) -> Any:
        """
        Build the boolean predicate expression.

        Priority:
        1) If `predicate_factory` is provided, use that.
        2) Else if `column` is provided, build a simple column-based predicate.
        """
        if self._predicate_factory is not None:
            return self._predicate_factory(ctx, value)

        if self._column is None:
            raise RuntimeError(
                "SqlAlchemyBoolFilter: either `column` or `predicate_factory` "
                "must be provided."
            )

        if self._use_is:
            # Suitable for real Boolean columns
            return self._column.is_(value)
        else:
            # For truthy expressions (case/when, exists, etc.)
            if value:
                return self._column
            return not_(self._column)
