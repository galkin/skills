"""The cascade names the step that rereads a Version from its `converter` (internal seam)."""

from __future__ import annotations

from lorekeep import cascade
from lorekeep.cascade.page import PageStep
from lorekeep.cascade.twin import TwinStep


def test_a_version_is_reread_by_the_step_whose_converter_it_carries() -> None:
    assert isinstance(cascade.step_of("md-twin"), TwinStep)
    assert cascade.step_of("trafilatura 2.0.0") == PageStep("trafilatura")
    assert cascade.step_of("markitdown 0.1.2") == PageStep("markitdown")


def test_a_browser_version_and_an_owner_version_have_no_step_to_reread_them() -> None:
    browser = cascade.step_of("trafilatura 2.0.0 via crawl4ai 0.9.5")
    owner = cascade.step_of("owner")

    assert isinstance(browser, cascade.Fallthrough) and "browser" in browser.reason
    assert isinstance(owner, cascade.Fallthrough) and "owner" in owner.reason
