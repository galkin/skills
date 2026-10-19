"""Parsing of ``$DAGU_OUTPUT_FILE`` (Dagu spec 012).

Records are ``name=value`` lines or ``name<<DELIM`` … ``DELIM`` blocks. Every emitted
name must be declared, every declared name emitted exactly once; a ``json`` output must
parse. A parse failure fails the attempt, so nothing from it is published.
"""

from __future__ import annotations

import json
import re

_DELIM = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class OutputError(Exception):
    pass


def parse_output_file(path: str, declared: dict[str, str]) -> dict[str, str]:
    """``declared`` maps output name -> type ('string' | 'json')."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        raw = b""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise OutputError(f"output file is not valid UTF-8: {e}") from e
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # the final line ending is not a record

    values: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if line == "":
            raise OutputError(f"empty line {i + 1} outside a multi-line value")
        if "<<" in line and "=" not in line.split("<<", 1)[0]:
            name, delim = line.split("<<", 1)
            if not _DELIM.match(delim):
                raise OutputError(f"invalid delimiter {delim!r} on line {i + 1}")
            body: list[str] = []
            i += 1
            while i < len(lines) and lines[i] != delim:
                body.append(lines[i])
                i += 1
            if i >= len(lines):
                raise OutputError(f"unclosed multi-line record {name!r}")
            value = "\n".join(body)
        elif "=" in line:
            name, value = line.split("=", 1)
        else:
            raise OutputError(f"line {i + 1} is neither name=value nor name<<DELIM: {line!r}")
        _publish(name, value, values, declared)
        i += 1

    missing = [n for n in declared if n not in values]
    if missing:
        raise OutputError(f"declared outputs not emitted: {', '.join(missing)}")
    return values


def _publish(name: str, value: str, values: dict[str, str], declared: dict[str, str]) -> None:
    if name not in declared:
        raise OutputError(f"undeclared output {name!r}")
    if name in values:
        raise OutputError(f"output {name!r} emitted more than once")
    if declared[name] == "json":
        try:
            json.loads(value)
        except ValueError as e:
            raise OutputError(f"output {name!r} is not valid JSON: {e}") from e
    values[name] = value
