from __future__ import annotations

from typing import Optional, List
import enum
import strawberry

from ...core.specs import SortField, SortSpec as CoreSortSpec


@strawberry.enum
class SortDirection(str, enum.Enum):
    ASC = "asc"
    DESC = "desc"


@strawberry.input
class SortFieldInput:
    """
    One sort rule: e.g. field='created_at', direction=ASC.

    `field` is a *logical* name understood by your infra
    (SqlAlchemySortFilter sort_map).
    """
    field: str
    direction: SortDirection = SortDirection.ASC


@strawberry.input
class SortInput:
    """
    List of sort rules in priority order.

    Example GQL:
      sort: {
        fields: [
          { field: "price", direction: ASC },
          { field: "created_at", direction: DESC }
        ]
      }
    """
    fields: List[SortFieldInput]


def sort_input_to_spec(inp: Optional[SortInput]) -> Optional[CoreSortSpec]:
    """
    Convert the Strawberry SortInput into the core SortSpec VO.
    """
    if inp is None or not inp.fields:
        return None

    return CoreSortSpec(
        fields=[
            CoreSortField(
                field=f.field,
                direction=f.direction.value,  # "asc" / "desc"
            )
            for f in inp.fields
        ]
    )