from __future__ import annotations

from dataclasses import fields as dataclass_fields, is_dataclass
from typing import Optional, List, Any
import enum
import strawberry

from ...core.specs import SortField as CoreSortField, SortSpec as CoreSortSpec

SORT_FIELD_METADATA_KEY = "sort_field"


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


def dataclass_sort_input_to_spec(inp: Optional[Any]) -> Optional[CoreSortSpec]:
    """Convert a dataclass-style Strawberry sort input to the core SortSpec.

    This is useful when you want to declare sort fields like any other
    GraphQL input fields (e.g. ``class ProductSortInput: price: SortDirection``)
    instead of using the generic ``SortInput`` wrapper where callers specify a
    list of ``{field, direction}`` pairs.

    Each dataclass attribute becomes a ``SortField`` entry (field name matches
    the attribute name unless ``metadata={"sort_field": "foo"}`` overrides it).
    Fields whose value is ``None`` are ignored, so clients only need to pass the
    sort rules they care about.
    """
    if inp is None:
        return None

    if not is_dataclass(inp):
        raise TypeError(
            "dataclass_sort_input_to_spec expects a dataclass instance."
        )

    sort_fields = []
    for dc_field in dataclass_fields(inp):
        direction = getattr(inp, dc_field.name)
        if direction is None:
            continue

        logical_name = dc_field.metadata.get(SORT_FIELD_METADATA_KEY, dc_field.name)
        sort_fields.append(
            CoreSortField(
                field=logical_name,
                direction=_normalize_direction(direction),
            )
        )

    if not sort_fields:
        return None

    return CoreSortSpec(fields=sort_fields)


def _normalize_direction(value: SortDirection | str) -> str:
    if isinstance(value, SortDirection):
        return value.value

    if isinstance(value, str):
        lowered = value.lower()
        if lowered not in ("asc", "desc"):
            raise ValueError(
                f"Invalid sort direction {value!r}. Expected 'asc' or 'desc'."
            )
        return lowered

    raise TypeError(
        "Sort direction must be a SortDirection enum or 'asc'/'desc' string."
    )
