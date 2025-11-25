from __future__ import annotations

from typing import Set, Tuple, Iterable

from strawberry.types import Info
from strawberry.types.nodes import SelectedField

Path = Tuple[str, ...]


def collect_field_paths(
        selected_fields: Iterable[SelectedField],
        parent_path: Path = (),
) -> Set[Path]:
    """
    Recursively flatten SelectedField tree into a set of path tuples.

    Example:
      courses { items { id translations { title } } }

    Might produce:
      ("items", "id")
      ("items", "translations")
      ("items", "translations", "title")
    """
    paths: Set[Path] = set()

    for field in selected_fields:
        current = (*parent_path, field.name)
        paths.add(current)

        if field.selections:
            paths |= collect_field_paths(field.selections, current)

    return paths


def get_root_field_paths(info: Info, root_field_name: str) -> Set[Path]:
    """
    Extract all selection paths under a given root field.

    Example: in a Query { courses { ... } }
      get_root_field_paths(info, "courses")
    returns all paths under the `courses` field.
    """
    paths: Set[Path] = set()
    for field in info.selected_fields:
        if field.name == root_field_name:
            paths |= collect_field_paths(field.selections)
    return paths


def has_any_under_prefix(paths: Set[Path], prefix: Path) -> bool:
    """
    Return True if any selection path starts with `prefix`.

    Example:
      prefix=("items", "translations")
      matches ("items", "translations"), ("items", "translations", "title"), etc.
    """
    plen = len(prefix)
    return any(p[:plen] == prefix for p in paths)


def fields_under_prefix(
        paths: Set[Path],
        prefix: Path,
        *,
        depth: int = 1,
        exclude: tuple[str, ...] = ("__typename",),
) -> Set[str]:
    """
    Collect field names immediately under a given prefix.

    Example:
      paths:
        ("items", "id")
        ("items", "translations", "title")
        ("items", "translations", "slug")
      prefix=("items", "translations"), depth=1
      => {"title", "slug"}

    depth is "how many steps after the prefix" to look.
      depth=1: children
      depth=2: grandchildren, etc.
    """
    plen = len(prefix)
    target_len = plen + depth

    result: Set[str] = set()
    for p in paths:
        if len(p) >= target_len and p[:plen] == prefix:
            name = p[plen + depth - 1]
            if name not in exclude:
                result.add(name)
    return result
