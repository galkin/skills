"""A Version's Provenance as YAML frontmatter.

Read with `yaml.BaseLoader`, which yields strings only: `safe_load` would turn a publisher's
`2026-08-13T00:00:00.0000000Z` into a `datetime`. Written with every string value quoted, so an
ETag's own quotes survive; a list of strings is written on one line, `["…", "…"]`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

import yaml

FENCE = b"---\n"

type Fields = Mapping[str, str | bool | int | Mapping[str, str | bool | int] | Sequence[str] | None]


class FrontmatterError(ValueError):
    """The file does not start with a YAML frontmatter block; the message says why, briefly."""


def parse(data: bytes) -> tuple[dict[str, Any], bytes]:
    """Split a Version file into its frontmatter (strings, lists of strings and one level of
    mappings) and body."""
    if not data.startswith(FENCE):
        raise FrontmatterError("no frontmatter")
    head, fence, body = data[len(FENCE) :].partition(b"\n" + FENCE)
    if not fence:
        raise FrontmatterError("the frontmatter is not closed by ---")
    try:
        fields = yaml.load(head.decode("utf-8"), Loader=yaml.BaseLoader) or {}
    except (UnicodeDecodeError, yaml.YAMLError) as error:
        raise FrontmatterError("the frontmatter is not YAML") from error
    if not isinstance(fields, dict):
        raise FrontmatterError("the frontmatter is not a mapping")
    return fields, body


def render(fields: Fields) -> bytes:
    """The frontmatter block for `fields`, in their order; `None` values and empty lists are
    left out."""
    lines = ["---"]
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, Mapping):
            lines.append(f"{key}:")
            lines += [f"  {k}: {_scalar(v)}" for k, v in value.items() if v is not None]
        elif isinstance(value, Sequence) and not isinstance(value, str):
            if value:
                lines.append(f"{key}: [{', '.join(_scalar(item) for item in value)}]")
        else:
            lines.append(f"{key}: {_scalar(value)}")
    lines.append("---")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _scalar(value: str | bool | int) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    # A JSON string is a valid YAML double-quoted scalar.
    return json.dumps(value, ensure_ascii=False)
