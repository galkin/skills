"""Loading, validation and normalization of a workflow file (Dagu subset v1).

Validation is the vendored JSON schema (``schemas/dag.schema.json``) plus the checks the
schema cannot express: unique ids, known ``depends`` targets, condition syntax, output
declarations, inferred dependencies from ``${steps.<id>.outputs.<name>}`` references
(spec 007) and acyclicity.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import jsonschema
import yaml

from .conditions import Condition
from .resolve import step_refs

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "dag.schema.json"
IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class SpecError(Exception):
    pass


@dataclass
class Param:
    name: str
    type: str = "string"
    default: str | None = None
    required: bool = False
    enum: list[str] | None = None


@dataclass
class RetryPolicy:
    limit: int = 0
    interval_sec: float = 0
    backoff: float = 1.0
    max_interval_sec: float | None = None
    exit_code: list[int] | None = None


@dataclass
class RepeatPolicy:
    repeat: str  # while | until
    condition: Condition | None = None
    interval_sec: float = 0
    backoff: float = 1.0
    max_interval_sec: float | None = None
    limit: int | None = None


@dataclass
class ContinueOn:
    failure: bool = False
    skipped: bool = False
    exit_code: list[int] = field(default_factory=list)
    output: list[str] = field(default_factory=list)
    mark_success: bool = False


@dataclass
class Handler:
    run: str
    env: list[tuple[str, str]] = field(default_factory=list)
    working_dir: str | None = None
    timeout_sec: int | None = None


@dataclass
class Step:
    id: str
    run: list[str]  # one entry for string form, several for array form
    script: bool = False  # multi-line string form
    depends: list[str] = field(default_factory=list)
    inferred: list[str] = field(default_factory=list)
    env: list[tuple[str, str]] = field(default_factory=list)
    working_dir: str | None = None
    timeout_sec: int | None = None
    outputs: dict[str, str] = field(default_factory=dict)  # name -> type
    preconditions: list[Condition] = field(default_factory=list)
    continue_on: ContinueOn = field(default_factory=ContinueOn)
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    repeat: RepeatPolicy | None = None
    description: str = ""

    @property
    def all_depends(self) -> list[str]:
        return self.depends + [d for d in self.inferred if d not in self.depends]


@dataclass
class Dag:
    name: str
    path: str
    params: list[Param]
    env: list[tuple[str, str]]
    steps: list[Step]
    handlers: dict[str, Handler]
    working_dir: str | None = None
    timeout_sec: int | None = None
    description: str = ""

    def step(self, step_id: str) -> Step:
        for s in self.steps:
            if s.id == step_id:
                return s
        raise KeyError(step_id)

    def descendants(self, step_id: str) -> list[str]:
        out: list[str] = []
        frontier = [step_id]
        while frontier:
            cur = frontier.pop()
            for s in self.steps:
                if cur in s.all_depends and s.id not in out:
                    out.append(s.id)
                    frontier.append(s.id)
        return out


def load(path: str | os.PathLike) -> Dag:
    path = str(path)
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise SpecError(f"{path}: the document must be a mapping")
    validate_schema(raw, path)
    return normalize(raw, path)


def validate_schema(raw: dict, path: str = "<memory>") -> None:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(raw), key=lambda e: list(e.absolute_path))
    if errors:
        lines = []
        for e in errors[:10]:
            where = "/".join(str(p) for p in e.absolute_path) or "<root>"
            lines.append(f"  {where}: {e.message[:200]}")
        raise SpecError(f"{path}: schema validation failed\n" + "\n".join(lines))


def normalize(raw: dict, path: str) -> Dag:
    name = raw.get("name") or Path(path).stem
    params = [
        Param(
            name=p["name"],
            type=p.get("type", "string"),
            default=None if "default" not in p else _scalar(p["default"]),
            required=bool(p.get("required", False)),
            enum=None if "enum" not in p else [_scalar(v) for v in p["enum"]],
        )
        for p in raw.get("params", [])
    ]
    seen_params = set()
    for p in params:
        if p.name in seen_params:
            raise SpecError(f"{path}: duplicate param {p.name!r}")
        seen_params.add(p.name)

    steps = [_step(s, path) for s in raw["steps"]]
    ids = [s.id for s in steps]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise SpecError(f"{path}: duplicate step id(s): {', '.join(sorted(dupes))}")
    for s in steps:
        for d in s.depends:
            if d not in ids:
                raise SpecError(f"{path}: step {s.id!r} depends on unknown step {d!r}")
        _infer(s, ids)
    _check_acyclic(steps, path)

    handlers = {k: _handler(v) for k, v in raw.get("handler_on", {}).items()}
    return Dag(
        name=name,
        path=path,
        params=params,
        env=_env(raw.get("env")),
        steps=steps,
        handlers=handlers,
        working_dir=raw.get("working_dir"),
        timeout_sec=raw.get("timeout_sec"),
        description=raw.get("description", ""),
    )


def _scalar(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _env(raw) -> list[tuple[str, str]]:
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [(k, _scalar(v)) for k, v in raw.items()]
    out: list[tuple[str, str]] = []
    for item in raw:
        if isinstance(item, str):
            k, _, v = item.partition("=")
            out.append((k, v))
        else:
            (k, v), = item.items()
            out.append((k, _scalar(v)))
    return out


def _conditions(raw, where: str) -> list[Condition]:
    if raw is None:
        return []
    items = [raw] if isinstance(raw, str) else raw
    out = []
    for i, item in enumerate(items):
        c = Condition.normalize(item)
        try:
            c.validate()
        except ValueError as e:
            raise SpecError(f"{where}/preconditions[{i}]: {e}") from e
        out.append(c)
    return out


def _continue_on(raw) -> ContinueOn:
    if raw is None:
        return ContinueOn()
    if raw == "failed":
        return ContinueOn(failure=True)
    if raw == "skipped":
        return ContinueOn(skipped=True)
    codes = raw.get("exit_code", [])
    outputs = raw.get("output", [])
    co = ContinueOn(
        failure=bool(raw.get("failure", False)),
        skipped=bool(raw.get("skipped", False)),
        exit_code=[codes] if isinstance(codes, int) else list(codes),
        output=[outputs] if isinstance(outputs, str) else list(outputs),
        mark_success=bool(raw.get("mark_success", False)),
    )
    for pat in co.output:
        if pat.startswith("num:"):
            raise SpecError("continue_on.output does not accept num: (matching is line by line)")
        if pat.startswith("re:"):
            try:
                re.compile(pat[3:])
            except re.error as e:
                raise SpecError(f"continue_on.output: invalid pattern {pat!r}: {e}") from e
    return co


def _backoff(raw) -> float:
    if raw is None or raw is False:
        return 1.0
    if raw is True:
        return 2.0
    return float(raw)


def _retry(raw) -> RetryPolicy:
    if raw is None:
        return RetryPolicy()
    return RetryPolicy(
        limit=int(raw.get("limit", 0)),
        interval_sec=float(raw.get("interval_sec", 0)),
        backoff=_backoff(raw.get("backoff")),
        max_interval_sec=None if "max_interval_sec" not in raw else float(raw["max_interval_sec"]),
        exit_code=None if "exit_code" not in raw else list(raw["exit_code"]),
    )


def _repeat(raw, where: str) -> RepeatPolicy | None:
    if raw is None:
        return None
    cond = None
    if "condition" in raw:
        cond = Condition(raw["condition"], raw.get("expected"))
        try:
            cond.validate()
        except ValueError as e:
            raise SpecError(f"{where}/repeat_policy: {e}") from e
    elif "expected" in raw:
        raise SpecError(f"{where}/repeat_policy: expected without condition")
    return RepeatPolicy(
        repeat=raw["repeat"],
        condition=cond,
        interval_sec=float(raw.get("interval_sec", 0)),
        backoff=_backoff(raw.get("backoff")),
        max_interval_sec=None if "max_interval_sec" not in raw else float(raw["max_interval_sec"]),
        limit=raw.get("limit"),
    )


def _step(raw: dict, path: str) -> Step:
    where = f"{path}: step {raw['id']!r}"
    run = raw["run"]
    if isinstance(run, str):
        if not run.strip():
            raise SpecError(f"{where}: run must not be empty")
        script = "\n" in run.strip()
        runs = [run]
    else:
        runs = [r for r in run if r.strip()]
        if not runs:
            raise SpecError(f"{where}: run has no non-empty entries")
        if any("\n" in r for r in runs):
            raise SpecError(f"{where}: array-form run entries must be single commands")
        script = False
    depends = raw.get("depends", [])
    depends = [depends] if isinstance(depends, str) else list(depends)
    outputs: dict[str, str] = {}
    for o in raw.get("outputs", []) or []:
        if o["name"] in outputs:
            raise SpecError(f"{where}: output {o['name']!r} declared twice")
        outputs[o["name"]] = o.get("type", "string")
    try:
        continue_on = _continue_on(raw.get("continue_on"))
    except SpecError as e:
        raise SpecError(f"{where}: {e}") from e
    return Step(
        id=raw["id"],
        run=runs,
        script=script,
        depends=depends,
        env=_env(raw.get("env")),
        working_dir=raw.get("working_dir"),
        timeout_sec=raw.get("timeout_sec"),
        outputs=outputs,
        preconditions=_conditions(raw.get("preconditions"), where),
        continue_on=continue_on,
        retry=_retry(raw.get("retry_policy")),
        repeat=_repeat(raw.get("repeat_policy"), where),
        description=raw.get("description", ""),
    )


def _handler(raw: dict) -> Handler:
    return Handler(
        run=raw["run"],
        env=_env(raw.get("env")),
        working_dir=raw.get("working_dir"),
        timeout_sec=raw.get("timeout_sec"),
    )


def _infer(step: Step, ids: list[str]) -> None:
    """Spec 007: a supported step-output reference in a value-resolved field orders the steps."""
    texts = list(step.run) + [v for _, v in step.env] + [c.condition for c in step.preconditions]
    if step.working_dir:
        texts.append(step.working_dir)
    if step.repeat and step.repeat.condition:
        texts.append(step.repeat.condition.condition)
    for text in texts:
        for producer, _ in step_refs(text):
            if producer in ids and producer != step.id and producer not in step.inferred:
                step.inferred.append(producer)


def _check_acyclic(steps: list[Step], path: str) -> None:
    graph = {s.id: s.all_depends for s in steps}
    state: dict[str, int] = {}

    def visit(node: str, trail: list[str]) -> None:
        if state.get(node) == 1:
            cycle = " -> ".join(trail[trail.index(node):] + [node])
            raise SpecError(f"{path}: dependency cycle {cycle}")
        if state.get(node) == 2:
            return
        state[node] = 1
        for dep in graph[node]:
            visit(dep, trail + [node])
        state[node] = 2

    for s in steps:
        visit(s.id, [])


def topological(steps: list[Step]) -> list[Step]:
    """Source order wherever dependencies allow it."""
    done: set[str] = set()
    order: list[Step] = []
    pending = list(steps)
    while pending:
        for s in pending:
            if all(d in done for d in s.all_depends):
                order.append(s)
                done.add(s.id)
                pending.remove(s)
                break
        else:  # pragma: no cover - acyclicity is checked at load time
            raise SpecError("unresolvable dependency order")
    return order


def resolve_params(dag: Dag, given: dict[str, str]) -> dict[str, str]:
    declared = {p.name: p for p in dag.params}
    unknown = sorted(set(given) - set(declared))
    if unknown:
        raise SpecError(f"unknown param(s): {', '.join(unknown)}")
    values: dict[str, str] = {}
    for p in dag.params:
        if p.name in given:
            values[p.name] = given[p.name]
        elif p.default is not None:
            values[p.name] = p.default
        elif p.required:
            raise SpecError(f"param {p.name!r} is required")
        else:
            continue
        v = values[p.name]
        if p.type == "integer" and not re.fullmatch(r"-?\d+", v):
            raise SpecError(f"param {p.name!r} must be an integer, got {v!r}")
        if p.type == "boolean" and v not in ("true", "false"):
            raise SpecError(f"param {p.name!r} must be true or false, got {v!r}")
        if p.enum is not None and v not in p.enum:
            raise SpecError(f"param {p.name!r} must be one of {p.enum}, got {v!r}")
    return values
