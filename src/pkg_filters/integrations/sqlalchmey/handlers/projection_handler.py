from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, TypeVar

from sqlalchemy.orm import load_only
from sqlalchemy.sql import Select

from ....core import QueryContext, BaseQuerySpec

Q = TypeVar("Q", bound=BaseQuerySpec[Any, Any])

# relation loader can be:
# - a ready-made loader option (selectinload(...), joinedload(...))
# - or a callable that receives the projection and returns a loader
RelationLoader = Callable[[Any], Any] | Any


@dataclass
class SqlAlchemyProjectionFilter(Generic[Q]):
    """
    Generic SQLAlchemy projection filter.

    - Trims scalar columns based on projection.scalar_fields
    - Applies relationship loader options based on boolean flags on projection
      (e.g. projection.include_translations, projection.include_prices, ...)
    """

    scalar_column_map: Dict[str, Any]
    relation_loaders: Dict[str, RelationLoader]
    projection_attr: str = "projection"
    skip_on_count: bool = True  # matches PipelineFilter protocol

    def apply(self, ctx: QueryContext[Select, Q]) -> QueryContext[Select, Q]:
        proj = getattr(ctx.spec, self.projection_attr, None)
        if proj is None:
            return ctx

        # ----- Scalar column trimming -----
        scalar_fields = getattr(proj, "scalar_fields", None)
        if scalar_fields:
            cols = [
                self.scalar_column_map[name]
                for name in scalar_fields
                if name in self.scalar_column_map
            ]
            if cols and len(cols) < len(self.scalar_column_map):
                ctx.stmt = ctx.stmt.options(load_only(*cols))

        # ----- Relationship loaders -----
        for flag_name, loader in self.relation_loaders.items():
            if getattr(proj, flag_name, False):
                option = loader(proj) if callable(loader) else loader
                ctx.stmt = ctx.stmt.options(option)

        return ctx
