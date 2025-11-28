from __future__ import annotations

from typing import TypeVar

from sqlalchemy.sql import Select

from ...core import BaseQuerySpec
from ...core.pipeline import QueryContext, Pipeline

Q = TypeVar("Q", bound=BaseQuerySpec[object, object])
SqlAlchemyQueryContext = QueryContext[Select, Q]
SqlAlchemyPipeline = Pipeline[Select, Q]
