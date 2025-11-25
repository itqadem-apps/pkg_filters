from __future__ import annotations

from typing import Any, Callable, Generic, Iterable, Sequence, TypeVar

from sqlalchemy import and_
from sqlalchemy.sql import Select

from ....core import BaseQuerySpec, RangeFilterVO, QueryContext, BaseRangeFilterHandler

Q = TypeVar("Q", bound=BaseQuerySpec[Any, Any])
T = TypeVar("T")

JoinFn = Callable[[Select, QueryContext[Select, Q], RangeFilterVO[T]], Select]
LoadOptionsFactory = Callable[[QueryContext[Select, Q], RangeFilterVO[T]], Iterable[Any]]
ColumnResolver = Callable[[QueryContext[Select, Q], RangeFilterVO[T]], Any]
ConditionList = Sequence[Any]
ConditionBuilder = Callable[[Any, RangeFilterVO[T]], ConditionList]


class SqlAlchemyRangeFilter(BaseRangeFilterHandler[Select, Q, T], Generic[Q, T]):
    """
    SQLAlchemy adapter for RangeFilter[T] with clean customization hooks.

    You can configure:
      - `column`               : a fixed SQLAlchemy column expression
      - `join_fn`              : optional function to apply joins
      - `load_options_factory` : optional factory for loader options (selectinload, joinedload, ...)
      - `condition_builder`    : optional function to build conditions from (column, range)

    This class already fits the PipelineFilter[Select, Q] protocol via BaseRangeFilterHandler.
    """

    def __init__(
            self,
            filter_attr: str,
            *,
            column: Any | None = None,
            join_fn: JoinFn[Q, T] | None = None,
            load_options_factory: LoadOptionsFactory[Q, T] | None = None,
            condition_builder: ConditionBuilder[T] | None = None,
    ) -> None:
        """
        :param filter_attr: attribute name on `filters` where the RangeFilter[T] lives.
        :param column: fixed SQLAlchemy column expression to compare against, OR
                       leave as None and override `resolve_column`.
        :param join_fn: optional function (stmt, ctx, rf) -> stmt that performs joins.
        :param load_options_factory: optional factory producing loader options for .options().
        :param condition_builder: optional override for how conditions are built from (column, rf).
        """
        super().__init__(filter_attr)
        self._column = column
        self._join_fn = join_fn
        self._load_options_factory = load_options_factory
        self._condition_builder = condition_builder

    # -------- Hooks from BaseRangeFilterHandler --------

    def prepare_stmt(
            self,
            stmt: Select,
            ctx: QueryContext[Select, Q],
            rf: RangeFilterVO[T],
    ) -> Select:
        if self._join_fn is not None:
            stmt = self._join_fn(stmt, ctx, rf)
        return stmt

    def apply_to_stmt(
            self,
            stmt: Select,
            ctx: QueryContext[Select, Q],
            rf: RangeFilterVO[T],
    ) -> Select:
        column = self.resolve_column(ctx, rf)
        conditions = self.build_conditions(column, rf)
        if not conditions:
            return stmt
        return stmt.where(and_(*conditions))

    def finalize_stmt(
            self,
            stmt: Select,
            ctx: QueryContext[Select, Q],
            rf: RangeFilterVO[T],
    ) -> Select:
        if ctx.for_count or self._load_options_factory is None:
            return stmt

        options = list(self._load_options_factory(ctx, rf))
        if not options:
            return stmt

        return stmt.options(*options)

    # -------- Extra hooks for subclasses / power users --------

    def resolve_column(self, ctx: QueryContext[Select, Q], rf: RangeFilterVO[T]) -> Any:
        """
        Determines which column to apply the range to.

        Default: use the fixed column passed to __init__.
        Override if you select the column dynamically (e.g. based on spec).
        """
        if self._column is None:
            raise RuntimeError(
                "SqlAlchemyRangeFilter: `column` is None and `resolve_column` "
                "was not overridden."
            )
        return self._column

    def build_conditions(self, column: Any, rf: RangeFilterVO[T]) -> ConditionList:
        """
        Default implementation builds standard [eq, gt, gte, lt, lte] conditions.

        Override, or pass a custom `condition_builder` to __init__, for custom logic.
        """
        if self._condition_builder is not None:
            return self._condition_builder(column, rf)

        conditions: list[Any] = []

        if rf.eq is not None:
            conditions.append(column == rf.eq)
        if rf.gt is not None:
            conditions.append(column > rf.gt)
        if rf.gte is not None:
            conditions.append(column >= rf.gte)
        if rf.lt is not None:
            conditions.append(column < rf.lt)
        if rf.lte is not None:
            conditions.append(column <= rf.lte)

        return conditions
