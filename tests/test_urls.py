"""URL normalisation and the host table, as the lookup and the Version file name see them."""

from __future__ import annotations

from pathlib import Path

import pytest

from lorekeep.project import load_project
from lorekeep.store import version_name
from lorekeep.urls import normalise, trust


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("https://Example.TEST/A/b#section", "https://example.test/A/b"),
        (
            "https://example.test/p?utm_source=x&ref=y&source=z&fbclid=1&gclid=2&view=3",
            "https://example.test/p?view=3",
        ),
        (
            "https://example.test/p?tabs=python&view=azure",
            "https://example.test/p?tabs=python&view=azure",
        ),
        (
            "https://example.test/p?view=azure&tabs=python",
            "https://example.test/p?tabs=python&view=azure",
        ),
        ("https://example.test/a/b/", "https://example.test/a/b"),
        ("https://example.test//a//b", "https://example.test/a/b"),
        ("HTTP://example.test/a", "http://example.test/a"),
        (
            "https://example.test/a%2Fb?accept=text%2Fmarkdown",
            "https://example.test/a%2Fb?accept=text/markdown",
        ),
    ],
)
def test_normalisation_without_a_host_rule(given: str, expected: str) -> None:
    assert normalise(given, ()) == expected


def test_a_twin_url_reduces_to_its_page_url_under_the_host_rule(tmp_path: Path) -> None:
    rules = load_project(tmp_path).hosts

    assert (
        normalise("https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md", rules)
        == "https://platform.claude.com/docs/en/build-with-claude/prompt-caching"
    )
    assert (
        normalise("https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.md", rules)
        == "https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html"
    )
    assert (
        normalise(
            "https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry?accept=text/markdown",
            rules,
        )
        == "https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry"
    )
    assert (
        normalise("https://docs.nvidia.com/nim/overview.md", rules)
        == "https://docs.nvidia.com/nim/overview.md"
    )


def test_the_file_name_is_host_path_and_sha8_with_unsafe_characters_as_dashes() -> None:
    name = version_name(
        "https://learn.microsoft.com/en-us/azure/foundry/what-is?view=x&tabs=y",
        "0123abcd" + "f" * 56,
    )

    assert name == "learn.microsoft.com--en-us-azure-foundry-what-is-view-x-tabs-y--0123abcd.md"


def test_the_longest_prefix_sets_publisher_and_authority_over_both_layers(tmp_path: Path) -> None:
    (tmp_path / "lorekeep.toml").write_text(
        '[[hosts]]\nprefix = "raw.githubusercontent.com/anthropics/"\n'
        'publisher = "anthropic"\nauthority = "primary"\ntwin = "raw"\n'
    )
    rules = load_project(tmp_path).hosts

    anthropic = trust("https://raw.githubusercontent.com/anthropics/sdk/main/README.md", rules)
    other = trust("https://raw.githubusercontent.com/someone/else/main/README.md", rules)
    aws = trust("https://docs.aws.amazon.com/bedrock/latest/userguide/x.html", rules)

    assert (anthropic.publisher, anthropic.authority, anthropic.warning) == (
        "anthropic",
        "primary",
        None,
    )
    assert (other.publisher, other.authority, other.warning) == ("github", "third-party", None)
    assert (aws.publisher, aws.authority) == ("aws", "primary")


def test_an_unknown_host_is_third_party_with_a_warning_naming_it(tmp_path: Path) -> None:
    rules = load_project(tmp_path).hosts

    unknown = trust("https://Docs.Example.test/guide", rules)

    assert (unknown.publisher, unknown.authority) == ("docs.example.test", "third-party")
    assert unknown.warning is not None
    assert "docs.example.test" in unknown.warning
    assert "lorekeep.toml" in unknown.warning
