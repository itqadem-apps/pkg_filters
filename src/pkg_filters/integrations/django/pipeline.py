from __future__ import annotations

from typing import TypeVar

from django.db.models import QuerySet

from ...core import BaseQuerySpec
from ...core.pipeline import QueryContext, Pipeline

Q = TypeVar("Q", bound=BaseQuerySpec[object, object])

DjangoQueryContext = QueryContext[QuerySet, Q]
DjangoPipeline = Pipeline[QuerySet, Q]

