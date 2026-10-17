"""The cascade `get` runs: an ordered list of steps, the first that yields Markdown wins.

Ticket 03 has the Twin step; the page step fetches the page once and converts it by its media
type (04: static HTML, 05: PDF); the browser (06) comes last and only when it is called for. A
step either returns what it `Fetched` or a `Fallthrough` saying why it declined, and the next
step runs.
"""

from __future__ import annotations

from collections.abc import Sequence

from lorekeep.cascade.browser import BrowserStep
from lorekeep.cascade.page import PageStep
from lorekeep.cascade.step import Fallthrough, Fetched, Request, Step
from lorekeep.cascade.twin import TwinStep

__all__ = ["BROWSER", "STEPS", "Fallthrough", "Fetched", "Request", "Step", "run_cascade"]

STEPS: tuple[Step, ...] = (TwinStep(), PageStep())
BROWSER: Step = BrowserStep()


def run_cascade(
    request: Request, steps: Sequence[Step], browser: Step | None = BROWSER
) -> Fetched | list[Fallthrough]:
    """The first step's `Fetched`, or every step's reason when none yielded Markdown.

    A host rule with `browser = true` goes to the browser without any plain request; otherwise
    the browser runs only when the last plain step says the page needs it.
    """
    reasons: list[Fallthrough] = []
    if not (request.rule is not None and request.rule.browser):
        for step in steps:
            outcome = step.attempt(request)
            if isinstance(outcome, Fetched):
                return outcome
            reasons.append(outcome)
        if not reasons or not reasons[-1].needs_browser:
            return reasons
    if browser is None:
        return reasons
    outcome = browser.attempt(request)
    if isinstance(outcome, Fetched):
        return outcome
    reasons.append(outcome)
    return reasons
