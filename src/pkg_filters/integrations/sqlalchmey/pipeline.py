from __future__ import annotations

from typing import TypeVar

from sqlalchemy.sql import Select

from core.pipeline import QueryContext, Pipeline
from core import BaseQuerySpec

Q = TypeVar("Q", bound=BaseQuerySpec[object, object])
SqlAlchemyQueryContext = QueryContext[Select, Q]
SqlAlchemyPipeline = Pipeline[Select, Q]
