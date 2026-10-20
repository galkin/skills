"""A file that is already text — JSON, YAML, plain text, CSV, XML — kept as received in one fence.

Nothing is converted: the bytes are decoded and wrapped in a fence named by the format, so an
OpenAPI schema or a values file is a Source like any page.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from urllib.parse import unquote, urlsplit

from lorekeep.cascade.step import Converted, Fallthrough

NAME = "verbatim"
"""The `converter` this converter writes, whole: there is no tool and no version to name."""

FORMATS: Mapping[str, tuple[str, str]] = {
    "application/json": ("json", "json"),
    "application/yaml": ("yaml", "yaml"),
    "text/yaml": ("yaml", "yaml"),
    "text/plain": ("text", "txt"),
    "text/csv": ("csv", "csv"),
    "application/xml": ("xml", "xml"),
    "text/xml": ("xml", "xml"),
}
"""Media type → (the fence's language, the Original's extension)."""
TYPES = tuple(FORMATS)

_BACKTICKS = re.compile(r"`{3,}")


def fence(text: str, language: str) -> str:
    """`text` in one fenced block, its fence longer than any run of backticks inside it."""
    longest = max((len(run) for run in _BACKTICKS.findall(text)), default=0)
    marker = "`" * max(3, longest + 1)
    end = "" if text.endswith("\n") else "\n"
    return f"{marker}{language}\n{text}{end}{marker}\n"


def last_segment(url: str) -> str | None:
    """The last segment of the address's path, decoded (`openapi_schema_rag_server.json`)."""
    name = unquote(urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1])
    return name or None


def converter_for(mediatype: str) -> Callable[[bytes, str, str | None], Converted | Fallthrough]:
    """The converter that keeps a file of `mediatype` verbatim, decoded by the charset the
    response named (UTF-8 when it named none, or one Python does not know)."""
    language, ext = FORMATS[mediatype]

    def convert(received: bytes, url: str, charset: str | None) -> Converted | Fallthrough:
        try:
            text = received.decode(charset or "utf-8", errors="replace")
        except LookupError:
            text = received.decode("utf-8", errors="replace")
        if not text.strip():
            return Fallthrough("no content: the file is empty")
        return Converted(
            markdown=fence(text, language).encode("utf-8"),
            converter=NAME,
            original_ext=ext,
            title=last_segment(url),
        )

    return convert
