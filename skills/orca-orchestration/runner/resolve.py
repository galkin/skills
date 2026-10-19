"""Value resolution (Dagu specs 003, 005, 006, 007).

Dagu-owned references are ``${params}``, ``${params.name}``, ``${env.NAME}`` and
``${steps.<id>.outputs.<name>}``. An escaped ``\\${...}`` is literal text; any other
braced text (``${NAME}``, ``$()``, nested paths) is preserved untouched for the shell.
A supported reference whose value is unavailable is preserved as written and reported
as a notice, never an error.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

IDENT = r"[A-Za-z][A-Za-z0-9_]*"
ENV_IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
_REF = re.compile(
    r"(?P<esc>\\?)\$\{(?P<body>params|params\.%s|env\.%s|steps\.%s\.outputs\.%s)\}"
    % (IDENT, ENV_IDENT, IDENT, IDENT)
)
_STEP_REF = re.compile(r"(?<!\\)\$\{steps\.(%s)\.outputs\.(%s)\}" % (IDENT, IDENT))


@dataclass
class Scope:
    """What a field may see. ``steps`` maps step id -> {output name: value}."""

    params: dict[str, str] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
    steps: dict[str, dict[str, str]] = field(default_factory=dict)
    steps_available: bool = True  # handler fields have no step-output scope (spec 007)


@dataclass
class Notice:
    reference: str
    reason: str


def resolve(text: str, scope: Scope, notices: list[Notice] | None = None) -> str:
    """Replace Dagu-owned references in ``text``; preserve what cannot resolve."""

    def sub(m: re.Match) -> str:
        ref = m.group(0)
        if m.group("esc"):
            return ref[1:]  # drop the escape marker, keep the text literal
        body = m.group("body")
        value = _lookup(body, scope, notices, ref)
        return ref if value is None else value

    return _REF.sub(sub, text)


def _lookup(body: str, scope: Scope, notices: list[Notice] | None, ref: str) -> str | None:
    def miss(reason: str) -> None:
        if notices is not None:
            notices.append(Notice(ref, reason))
        return None

    if body == "params":
        return json.dumps(scope.params, sort_keys=True)
    ns, _, rest = body.partition(".")
    if ns == "params":
        return scope.params[rest] if rest in scope.params else miss("unknown_param")
    if ns == "env":
        return scope.env[rest] if rest in scope.env else miss("unknown_env")
    # steps.<id>.outputs.<name>
    if not scope.steps_available:
        return miss("namespace_unavailable")
    step_id, _, name = rest.partition(".outputs.")
    outputs = scope.steps.get(step_id)
    if outputs is None:
        return miss("unknown_step_id")
    if name not in outputs:
        return miss("unknown_output_name")
    return outputs[name]


def step_refs(text: str) -> list[tuple[str, str]]:
    """Unescaped ``${steps.<id>.outputs.<name>}`` references in ``text`` (spec 007 inferred deps)."""
    return [(m.group(1), m.group(2)) for m in _STEP_REF.finditer(text)]


def is_single_ref(text: str) -> bool:
    """True when ``text`` is exactly one whole reference (used by ``num:`` thresholds)."""
    m = _REF.fullmatch(text.strip())
    return bool(m) and not m.group("esc")
