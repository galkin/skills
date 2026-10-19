"""The condition model of Dagu spec 023, shared by preconditions and repeat_policy.

A condition entry is ``{condition, expected?, negate?}``. With ``expected`` it is a
value match: the resolved condition text is data and is compared literally (any line
equal), by regex (``re:``, any line matches) or numerically (``num:<op><number>``, the
whole trimmed value). Without ``expected`` it is a command check: the text runs in the
shell and exit 0 means met. ``negate`` inverts met/not-met but never an evaluation
error, which is a failure, not a loop answer.
"""

from __future__ import annotations

import math
import re
import subprocess
from dataclasses import dataclass

from .resolve import Scope, is_single_ref, resolve

_NUM = re.compile(r"^\s*(>=|<=|>|<)\s*(.+?)\s*$")


class EvalError(Exception):
    """The condition itself could not be evaluated (spec 023 'evaluation error')."""


@dataclass(frozen=True)
class Condition:
    condition: str
    expected: str | None = None
    negate: bool = False

    @classmethod
    def normalize(cls, raw) -> "Condition":
        if isinstance(raw, str):
            return cls(raw)
        return cls(raw["condition"], raw.get("expected"), bool(raw.get("negate", False)))

    def validate(self) -> None:
        if not self.condition.strip():
            raise ValueError("condition must not be empty")
        if self.expected is None:
            return
        if not self.expected.strip():
            raise ValueError("expected must not be empty")
        if self.expected.startswith("re:"):
            pattern = self.expected[3:]
            if not pattern.strip():
                raise ValueError("re: pattern must not be empty")
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f"invalid re: pattern {pattern!r}: {e}") from e
        elif self.expected.startswith("num:"):
            m = _NUM.match(self.expected[4:])
            if not m:
                raise ValueError(f"num: comparison must be <op><number>, got {self.expected!r}")
            number = m.group(2)
            if not is_single_ref(number) and _to_float(number) is None:
                raise ValueError(f"num: threshold {number!r} is neither a number nor one reference")

    def check(self, scope: Scope, env: dict[str, str], cwd: str | None, shell: list[str]) -> bool:
        """Met after negation; raises EvalError on an evaluation error."""
        actual = resolve(self.condition, scope)
        if self.expected is None:
            met = _command_check(actual, env, cwd, shell)
        else:
            met = _value_match(actual, self.expected, scope)
        return (not met) if self.negate else met


def _value_match(actual: str, expected: str, scope: Scope) -> bool:
    lines = actual.split("\n")
    if expected.startswith("re:"):
        pattern = re.compile(expected[3:])
        return any(pattern.search(line) for line in lines)
    if expected.startswith("num:"):
        m = _NUM.match(expected[4:])
        if not m:
            raise EvalError(f"invalid num: comparison {expected!r}")
        op, number = m.group(1), m.group(2)
        threshold = _to_float(resolve(number, scope))
        if threshold is None:
            raise EvalError(f"num: threshold {number!r} did not resolve to a number")
        value = _to_float(actual.strip())
        if value is None:
            raise EvalError(f"value {actual.strip()!r} is not a number for {expected!r}")
        return {">": value > threshold, ">=": value >= threshold, "<": value < threshold, "<=": value <= threshold}[op]
    return any(line == expected for line in lines)


def _command_check(command: str, env: dict[str, str], cwd: str | None, shell: list[str]) -> bool:
    try:
        proc = subprocess.run(shell + [command], env=env, cwd=cwd, capture_output=True)
    except OSError:
        return False  # the process could not be started: not met (spec 023)
    return proc.returncode == 0


def _to_float(text: str) -> float | None:
    try:
        value = float(text.replace("_", ""))
    except ValueError:
        return None
    return value if math.isfinite(value) else None
