"""The cascade `get` runs: an ordered list of steps, the first that yields Markdown wins.

Ticket 03 has the Twin step; the page step fetches the page once and converts it by its media
type (05: PDF; 04 adds static HTML), and 06 appends the browser. A step either
returns what it `Fetched` or a `Fallthrough` saying why it declined, and the next step runs.
"""

from __future__ import annotations

from collections.abc import Sequence

from lorekeep.cascade.page import PageStep
from lorekeep.cascade.step import Fallthrough, Fetched, Request, Step
from lorekeep.cascade.twin import TwinStep

__all__ = ["STEPS", "Fallthrough", "Fetched", "Request", "Step", "run_cascade"]

STEPS: tuple[Step, ...] = (TwinStep(), PageStep())


def run_cascade(request: Request, steps: Sequence[Step]) -> Fetched | list[Fallthrough]:
    """The first step's `Fetched`, or every step's reason when none yielded Markdown."""
    reasons: list[Fallthrough] = []
    for step in steps:
        outcome = step.attempt(request)
        if isinstance(outcome, Fetched):
            return outcome
        reasons.append(outcome)
    return reasons
