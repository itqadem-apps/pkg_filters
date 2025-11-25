from __future__ import annotations

from datetime import datetime, date, time
from decimal import Decimal, InvalidOperation
from typing import Optional, TypeVar, Type, Callable, Any

from graphql.language import ast as graphql_ast
import strawberry

from ...core import RangeFilterVO, DateTimeRangeFilterVO, DateRangeFilterVO, TimeRangeFilterVO

T = TypeVar("T")
VO = TypeVar("VO")


# ---------- Scalars ----------


def _serialize_lenient_datetime(value: datetime | None) -> Optional[str]:
    if value is None:
        return None

    iso = value.isoformat()
    if value.tzinfo is not None and iso.endswith("+00:00"):
        return iso[:-6] + "Z"
    return iso


def _parse_lenient_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None
        if trimmed.endswith("Z"):
            trimmed = trimmed[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(trimmed)
        except ValueError as exc:
            raise ValueError(f"Value cannot represent a DateTime: {value!r}. Expected ISO-8601 string.") from exc

    raise ValueError(f"Value cannot represent a DateTime: {value!r}.")


def _parse_lenient_datetime_literal(ast_node, _variables=None) -> Optional[datetime]:
    if isinstance(ast_node, graphql_ast.NullValueNode):
        return None

    if isinstance(ast_node, graphql_ast.StringValueNode):
        return _parse_lenient_datetime(ast_node.value)

    raise ValueError("DateTime values must be provided as string literals.")


LenientNullableDateTime = strawberry.scalar(
    datetime,
    name="NullableDateTime",
    description="ISO 8601 DateTime that treats empty strings as null.",
    serialize=_serialize_lenient_datetime,
    parse_value=_parse_lenient_datetime,
    parse_literal=_parse_lenient_datetime_literal,
)


def _serialize_lenient_decimal(value: Decimal | None) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _parse_lenient_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        return Decimal(str(value))

    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None
        try:
            return Decimal(trimmed)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"Value cannot represent a Decimal: {value!r}. Expected numeric string.") from exc

    raise ValueError(f"Value cannot represent a Decimal: {value!r}.")


def _parse_lenient_decimal_literal(ast_node, _variables=None) -> Optional[Decimal]:
    if isinstance(ast_node, graphql_ast.NullValueNode):
        return None

    if isinstance(ast_node, (
        graphql_ast.StringValueNode,
        graphql_ast.IntValueNode,
        graphql_ast.FloatValueNode,
    )):
        return _parse_lenient_decimal(ast_node.value)

    raise ValueError("Decimal values must be provided as numeric or string literals.")


LenientNullableDecimal = strawberry.scalar(
    Decimal,
    name="NullableDecimal",
    description="Decimal scalar that treats empty strings as null.",
    serialize=_serialize_lenient_decimal,
    parse_value=_parse_lenient_decimal,
    parse_literal=_parse_lenient_decimal_literal,
)


# ========== Concrete range inputs ==========

@strawberry.input
class IntRangeFilterInput:
    eq: Optional[int] = None
    gt: Optional[int] = None
    gte: Optional[int] = None
    lt: Optional[int] = None
    lte: Optional[int] = None

    def to_vo(self) -> RangeFilterVO[int]:
        return DateTimeRangeFilterVO(
            eq=self.eq,
            gt=self.gt,
            gte=self.gte,
            lt=self.lt,
            lte=self.lte,
        )


@strawberry.input
class FloatRangeFilterInput:
    eq: Optional[float] = None
    gt: Optional[float] = None
    gte: Optional[float] = None
    lt: Optional[float] = None
    lte: Optional[float] = None

    def to_vo(self) -> RangeFilterVO[float]:
        return RangeFilterVO(
            eq=self.eq,
            gt=self.gt,
            gte=self.gte,
            lt=self.lt,
            lte=self.lte,
        )


@strawberry.input
class DecimalRangeFilterInput:
    eq: Optional[LenientNullableDecimal] = None
    gt: Optional[LenientNullableDecimal] = None
    gte: Optional[LenientNullableDecimal] = None
    lt: Optional[LenientNullableDecimal] = None
    lte: Optional[LenientNullableDecimal] = None

    def to_vo(self) -> RangeFilterVO[Decimal]:
        return RangeFilterVO(
            eq=self.eq,
            gt=self.gt,
            gte=self.gte,
            lt=self.lt,
            lte=self.lte,
        )


@strawberry.input
class DateTimeRangeFilterInput:
    eq: Optional[LenientNullableDateTime] = None
    gt: Optional[LenientNullableDateTime] = None
    gte: Optional[LenientNullableDateTime] = None
    lt: Optional[LenientNullableDateTime] = None
    lte: Optional[LenientNullableDateTime] = None

    def to_vo(self) -> DateTimeRangeFilterVO:
        return DateTimeRangeFilterVO(
            eq=self.eq,
            gt=self.gt,
            gte=self.gte,
            lt=self.lt,
            lte=self.lte,
        )


@strawberry.input
class DateRangeFilterInput:
    eq: Optional[date] = None
    gt: Optional[date] = None
    gte: Optional[date] = None
    lt: Optional[date] = None
    lte: Optional[date] = None

    def to_vo(self) -> DateRangeFilterVO:
        return RangeFilterVO(
            eq=self.eq,
            gt=self.gt,
            gte=self.gte,
            lt=self.lt,
            lte=self.lte,
        )


@strawberry.input
class TimeRangeFilterInput:
    eq: Optional[time] = None
    gt: Optional[time] = None
    gte: Optional[time] = None
    lt: Optional[time] = None
    lte: Optional[time] = None

    def to_vo(self) -> TimeRangeFilterVO:
        return TimeRangeFilterVO(
            eq=self.eq,
            gt=self.gt,
            gte=self.gte,
            lt=self.lt,
            lte=self.lte,
        )


# ========== Generic mapper ==========

def _range_input_to_vo_generic(
        inp,
        vo_cls: Type[VO],
        cast: Callable[[T], T] | None = None,
) -> Optional[VO]:
    if inp is None:
        return None

    def _c(x):
        return cast(x) if (cast is not None and x is not None) else x

    return vo_cls(
        eq=_c(inp.eq),
        lt=_c(inp.lt),
        lte=_c(inp.lte),
        gt=_c(inp.gt),
        gte=_c(inp.gte),
    )


# ========== Typed helpers ==========

def int_range_input_to_vo(
        inp: Optional[IntRangeFilterInput],
) -> Optional[RangeFilterVO[int]]:
    # Runtime constructor is RangeFilterVO, not RangeFilterVO[int]
    return _range_input_to_vo_generic(inp, RangeFilterVO)


def float_range_input_to_vo(
        inp: Optional[FloatRangeFilterInput],
) -> Optional[RangeFilterVO[float]]:
    return _range_input_to_vo_generic(inp, RangeFilterVO)


def decimal_range_input_to_vo(
        inp: Optional[DecimalRangeFilterInput],
) -> Optional[RangeFilterVO[Decimal]]:
    return _range_input_to_vo_generic(inp, RangeFilterVO)


def datetime_range_input_to_vo(
        inp: Optional[DateTimeRangeFilterInput],
) -> Optional[DateTimeRangeFilterVO]:
    return _range_input_to_vo_generic(inp, DateTimeRangeFilterVO)


def date_range_input_to_vo(
        inp: Optional[DateRangeFilterInput],
) -> Optional[RangeFilterVO[date]]:
    # Uses generic RangeFilterVO[date]; good if your DB column is DATE
    return _range_input_to_vo_generic(inp, RangeFilterVO)


def time_range_input_to_vo(
        inp: Optional[TimeRangeFilterInput],
) -> Optional[RangeFilterVO[time]]:
    # Uses generic RangeFilterVO[time]; good for TIME columns
    return _range_input_to_vo_generic(inp, RangeFilterVO)
