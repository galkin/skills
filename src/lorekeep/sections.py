"""Sections: the text under each Markdown heading, the unit the Index searches and answers with.

Pure text: a Version's body in, its Sections out, each with its heading path and the line its
heading sits on, cut again at paragraph boundaries when it is larger than `SECTION_BYTES`.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

SECTION_BYTES = 4096


@dataclass(frozen=True)
class Section:
    heading: str
    line: int
    body: str


_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)[ \t#]*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def split(text: str, first_line: int = 1) -> Iterator[Section]:
    """The text under each Markdown heading, with its heading path (`A > B`) and the line its
    heading sits on (`first_line` is the body's first line in the file). A Section over
    `SECTION_BYTES` is cut again at paragraph boundaries; a code fence is never cut."""
    path: list[tuple[int, str]] = []
    heading, start, lines = "", first_line, []
    fence: str | None = None
    for number, line in enumerate(text.splitlines(), start=first_line):
        opener = _FENCE.match(line)
        if fence is not None:
            if opener and opener.group(1)[0] == fence[0] and len(opener.group(1)) >= len(fence):
                fence = None
        elif opener:
            fence = opener.group(1)
        else:
            match = _HEADING.match(line)
            if match:
                yield from _slices(heading, start, lines)
                level = len(match.group(1))
                path = [(lvl, name) for lvl, name in path if lvl < level]
                path.append((level, match.group(2).strip()))
                heading = " > ".join(name for _, name in path)
                start, lines = number, []
                continue
        if not lines and heading == "" and not line.strip():
            start = number + 1
            continue
        lines.append((number, line))
    yield from _slices(heading, start, lines)


def _slices(heading: str, start: int, lines: list[tuple[int, str]]) -> Iterator[Section]:
    """Cut one heading's text into Sections of at most `SECTION_BYTES` at paragraph boundaries.

    A paragraph (or a whole code fence) larger than the limit is cut at line boundaries when it
    is prose and kept whole when it is a fence."""
    blocks = _blocks(lines)
    if not any(text.strip() for _, text in lines):
        return
    current: list[tuple[int, str]] = []
    size = 0
    line = start
    for block in blocks:
        block_size = sum(len(text.encode()) + 1 for _, text in block)
        if current and size + block_size > SECTION_BYTES:
            yield Section(heading, line, _join(current))
            current, size, line = [], 0, block[0][0]
        if block_size > SECTION_BYTES and not _FENCE.match(block[0][1]):
            for number, text in block:
                text_size = len(text.encode()) + 1
                if current and size + text_size > SECTION_BYTES:
                    yield Section(heading, line, _join(current))
                    current, size, line = [], 0, number
                current.append((number, text))
                size += text_size
            continue
        current += block
        size += block_size
    if any(text.strip() for _, text in current):
        yield Section(heading, line, _join(current))


def _blocks(lines: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    """Paragraphs and code fences, each with the blank lines before the next one.

    A block never starts with a blank line: blank lines belong to the block before them (or
    to none, at the start), so a fence is recognised by its first line and a slice's `line`
    points at text."""
    blocks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    fence: str | None = None
    for number, text in lines:
        opener = _FENCE.match(text)
        if fence is not None:
            current.append((number, text))
            if opener and opener.group(1)[0] == fence[0] and len(opener.group(1)) >= len(fence):
                fence = None
            continue
        if not text.strip():
            if current:
                current.append((number, text))
                blocks.append(current)
                current = []
            elif blocks:
                blocks[-1].append((number, text))
            continue
        if opener:
            if current:
                blocks.append(current)
                current = []
            fence = opener.group(1)
        current.append((number, text))
    if current:
        blocks.append(current)
    return blocks


def _join(lines: list[tuple[int, str]]) -> str:
    return "\n".join(text for _, text in lines).strip("\n")
