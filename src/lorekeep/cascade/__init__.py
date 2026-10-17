"""The cascade `get` runs: an ordered list of steps, the first that yields Markdown wins.

The Twin step asks for the publisher's Markdown; the page step fetches the page once and
converts it by its media type (static HTML, PDF); the browser comes last and only when it is
called for. A step either returns what it `Fetched` or a `Fallthrough` saying why it declined,
and the next step runs.
"""

from __future__ import annotations

from dataclasses import replace

from lorekeep import sections
from lorekeep.cascade import browser, twin
from lorekeep.cascade.browser import BrowserStep
from lorekeep.cascade.page import PageStep
from lorekeep.cascade.step import Fallthrough, Fetched, Request, Same, Step
from lorekeep.cascade.twin import TwinStep

__all__ = [
    "BROWSER",
    "STEPS",
    "Fallthrough",
    "Fetched",
    "Request",
    "Same",
    "Step",
    "run_cascade",
    "step_of",
]

STEPS: tuple[Step, ...] = (TwinStep(), PageStep())
BROWSER: Step = BrowserStep()
STRUCTURELESS = 20_000
ONE_FENCE = ("raw-twin", "verbatim")
"""Converters that keep a file in one fence: no headings is expected there, not a warning."""
"""Characters of Markdown over which a Version with no heading below its title is worth a
warning: every Section of it has the same heading path, so a hit cannot say where it is."""


def step_of(converter: str) -> Step | Fallthrough:
    """The step that rereads a Version carrying `converter` (its first word names the step's
    converter: `md-twin`, `raw-twin`, `trafilatura`, `markitdown`, `verbatim`), or why none
    does: the browser's mark (`via crawl4ai`) means bytes that differ on every visit, and a
    converter no step writes (`owner`) has no step. The only reader of the `converter` string."""
    if browser.via_browser(converter):
        return Fallthrough(browser.NEVER_REREAD)
    name = converter.split(" ", 1)[0]
    if name in (twin.CONVERTER, twin.RAW_CONVERTER):
        return STEPS[0]
    step = PageStep.of(name)
    if step is None:
        return Fallthrough(f"no step converts with {name or 'no converter'}")
    return step


def run_cascade(request: Request) -> Fetched | list[Fallthrough]:
    """The first step's `Fetched`, or every step's reason when none yielded Markdown.

    A host rule with `browser = true` goes to the browser without any plain request; otherwise
    the browser runs only when the last plain step says the page needs it. A `final` reason
    ends the cascade as the last of the reasons.
    """
    reasons: list[Fallthrough] = []
    if not (request.rule is not None and request.rule.browser):
        for step in STEPS:
            outcome = step.attempt(request)
            if isinstance(outcome, Fetched):
                return structure_warned(outcome)
            reasons.append(outcome)
            if outcome.final:
                return reasons
        if not reasons[-1].needs_browser:
            return reasons
    outcome = BROWSER.attempt(request)
    if isinstance(outcome, Fetched):
        return structure_warned(outcome)
    reasons.append(outcome)
    return reasons


def structure_warned(fetched: Fetched) -> Fetched:
    """`fetched` with a warning when its Markdown is over `STRUCTURELESS` characters and has at
    most one heading (the title, or the heading the converter wrote for it, which on EUR-Lex is a
    footer's `Need help?`). The Markdown is left as it is."""
    if fetched.converter in ONE_FENCE:
        return fetched
    markdown = fetched.markdown.decode("utf-8", errors="replace")
    if len(markdown) <= STRUCTURELESS or sections.headings(markdown) > 1:
        return fetched
    warning = "no headings; search answers with the whole page as one Section"
    return replace(fetched, warnings=(*fetched.warnings, warning))
