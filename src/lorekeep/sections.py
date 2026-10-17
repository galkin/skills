"""Sections: the text under each Markdown heading, the unit the Index searches and answers with.

Pure text: a Version's body in, its Sections out, each with its heading path, the line its heading
sits on and the line its text starts on, cut again at paragraph boundaries when it is larger than
`SECTION_BYTES`.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum

SECTION_BYTES = 4096


@dataclass(frozen=True)
class Section:
    """`heading` is the path (`A > B`, `""` before any heading); `heading_line` the line its
    heading sits on (`None` before any heading); `line` the line `body` starts on, so the body's
    n-th line is the file's line `line + n`."""

    heading: str
    heading_line: int | None
    line: int
    body: str


_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)[ \t#]*$")
# A fence opener is a line that is nothing but the fence and an optional info string (which, for
# a backtick fence, holds no backtick); a closer is nothing but the fence.
_OPENER = re.compile(r"^ {0,3}(?:(`{3,})[^`]*|(~{3,}).*)$")
_CLOSER = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
_BACKTICK_RUN = re.compile(r"`{3,}")
_PERMALINK = re.compile(r"\s*\[(?:#|\\#|¶|🔗)?\]\([^)]*\)")


class _Kind(Enum):
    OPENER = "opener"
    CODE = "code"


def heading_name(text: str) -> str:
    """A heading's text without the permalinks a converter left in it (`[#](…#anchor)`)."""
    return _PERMALINK.sub("", text).strip()


def _closes(line: str, fence: str) -> bool:
    match = _CLOSER.match(line)
    return bool(match) and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence)


def _opens_inline(line: str) -> bool:
    """A line of text that ends with an unpaired backtick fence, as a converter writes
    `Example: ```` before a block whose closer stands on a line of its own."""
    runs = _BACKTICK_RUN.findall(line)
    return len(runs) % 2 == 1 and line.rstrip().endswith("```")


def _kinds(texts: list[str]) -> list[_Kind | None]:
    """Which lines are code: a fence opener, or a line inside a fence (its closer included).

    A fence opens on a line that is nothing but the fence, or after a line of text that ends with
    one (the text line itself stays text); it closes at its closer, and a fence never closed ends
    at the next heading, so one stray fence cannot swallow the rest of a page."""
    kinds: list[_Kind | None] = [None] * len(texts)
    at = 0
    while at < len(texts):
        opener = _OPENER.match(texts[at])
        if opener:
            fence, first = opener.group(1) or opener.group(2), at + 1
            kinds[at] = _Kind.OPENER
        elif _opens_inline(texts[at]):
            fence, first = "```", at + 1
        else:
            at += 1
            continue
        end = next((n for n in range(first, len(texts)) if _closes(texts[n], fence)), None)
        if end is None:
            heading = next((n for n in range(first, len(texts)) if _HEADING.match(texts[n])), None)
            end = (len(texts) if heading is None else heading) - 1
        for n in range(first, end + 1):
            kinds[n] = _Kind.CODE
        at = end + 1
    return kinds


def headings(text: str) -> int:
    """How many lines of `text` are Markdown headings; a `#` line inside a code fence is code."""
    texts = text.splitlines()
    kinds = _kinds(texts)
    return sum(
        1 for line, kind in zip(texts, kinds, strict=True) if kind is None and _HEADING.match(line)
    )


def split(text: str, first_line: int = 1) -> Iterator[Section]:
    """The text under each Markdown heading, with its heading path (`A > B`, permalinks dropped)
    and the lines its heading and its text sit on (`first_line` is the body's first line in the
    file). A Section over `SECTION_BYTES` is cut again at paragraph boundaries; a code fence is
    never cut."""
    texts = text.splitlines()
    kinds = _kinds(texts)
    path: list[tuple[int, str]] = []
    heading, heading_line = "", None
    lines: list[tuple[int, str, _Kind | None]] = []
    for offset, (line, kind) in enumerate(zip(texts, kinds, strict=True)):
        number = first_line + offset
        match = _HEADING.match(line) if kind is None else None
        if match:
            yield from _slices(heading, heading_line, lines)
            level = len(match.group(1))
            path = [(lvl, name) for lvl, name in path if lvl < level]
            path.append((level, heading_name(match.group(2))))
            heading = " > ".join(name for _, name in path)
            heading_line, lines = number, []
            continue
        lines.append((number, line, kind))
    yield from _slices(heading, heading_line, lines)


def _slices(
    heading: str, heading_line: int | None, lines: list[tuple[int, str, _Kind | None]]
) -> Iterator[Section]:
    """Cut one heading's text into Sections of at most `SECTION_BYTES` at paragraph boundaries.

    A paragraph (or a whole code fence) larger than the limit is cut at line boundaries when it
    is prose and kept whole when it is a fence."""
    if not any(text.strip() for _, text, _ in lines):
        return
    current: list[tuple[int, str]] = []
    size = 0
    for block, fenced in _blocks(lines):
        block_size = sum(len(text.encode()) + 1 for _, text in block)
        if current and size + block_size > SECTION_BYTES:
            yield _section(heading, heading_line, current)
            current, size = [], 0
        if block_size > SECTION_BYTES and not fenced:
            for number, text in block:
                text_size = len(text.encode()) + 1
                if current and size + text_size > SECTION_BYTES:
                    yield _section(heading, heading_line, current)
                    current, size = [], 0
                current.append((number, text))
                size += text_size
            continue
        current += block
        size += block_size
    if any(text.strip() for _, text in current):
        yield _section(heading, heading_line, current)


def _section(heading: str, heading_line: int | None, lines: list[tuple[int, str]]) -> Section:
    """One Section from its lines; it starts at the first line `_join` keeps."""
    line = next((number for number, text in lines if text), lines[0][0])
    return Section(heading, heading_line, line, _join(lines))


def _blocks(
    lines: list[tuple[int, str, _Kind | None]],
) -> list[tuple[list[tuple[int, str]], bool]]:
    """Paragraphs and code fences, each with the blank lines before the next one, and whether it
    is a fence.

    A block never starts with a blank line: blank lines belong to the block before them (or
    to none, at the start), so a slice's `line` points at text. A blank line inside a fence
    belongs to the fence."""
    blocks: list[tuple[list[tuple[int, str]], bool]] = []
    current: list[tuple[int, str]] = []
    fenced = False
    for number, text, kind in lines:
        if kind is _Kind.CODE:
            current.append((number, text))
            continue
        if kind is _Kind.OPENER:
            if current:
                blocks.append((current, fenced))
            current, fenced = [(number, text)], True
            continue
        if not text.strip():
            if current:
                current.append((number, text))
                blocks.append((current, fenced))
                current, fenced = [], False
            elif blocks:
                blocks[-1][0].append((number, text))
            continue
        if fenced:
            blocks.append((current, fenced))
            current, fenced = [], False
        current.append((number, text))
    if current:
        blocks.append((current, fenced))
    return blocks


def _join(lines: list[tuple[int, str]]) -> str:
    return "\n".join(text for _, text in lines).strip("\n")
