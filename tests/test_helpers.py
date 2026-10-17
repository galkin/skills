"""The two Store helpers: a Version written straight from a fixture, and a Version aged."""

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from tests.support import FIXTURES, age_version, run_cli, write_version

FOUNDRY_TWIN = FIXTURES / "ms-foundry.twin"
FOUNDRY_URL = "https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry?accept=text/markdown"


def read_version(path: Path) -> tuple[dict[str, Any], bytes]:
    """A Version's frontmatter, read the way the spec says (`yaml.BaseLoader`), and its body."""
    data = path.read_bytes()
    assert data.startswith(b"---\n")
    head, body = data[4:].split(b"\n---\n", 1)
    return yaml.load(head.decode(), Loader=yaml.BaseLoader), body


def test_a_version_written_from_a_fixture_keeps_the_body_verbatim(tmp_path: Path) -> None:
    received = (FOUNDRY_TWIN / "body.md").read_bytes()

    path = write_version(tmp_path, FOUNDRY_TWIN, fetched_at="2026-10-01T08:00:00Z")

    frontmatter, body = read_version(path)
    digest = hashlib.sha256(received).hexdigest()
    assert body == received
    assert path.parent == tmp_path
    assert path.name.endswith(f"--{digest[:8]}.md")
    assert frontmatter["fetched_at"] == "2026-10-01T08:00:00Z"
    assert frontmatter["sha256"] == digest
    assert frontmatter["etag"] == '"RYzzG3LLzfqUX6b79i4xKDnTE/w="'
    assert frontmatter["last_modified"] == "Tue, 13 Oct 2026 16:17:35 GMT"
    assert frontmatter["original"]["url"] == FOUNDRY_URL
    assert frontmatter["original"]["sha256"] == digest
    assert frontmatter["original"]["mediatype"] == "text/markdown"
    assert {"url", "publisher", "authority", "converter"} <= set(frontmatter)
    assert "1 Version" in run_cli(["status", "--store", str(tmp_path)]).stdout


def test_a_written_version_takes_chosen_fields(tmp_path: Path) -> None:
    path = write_version(
        tmp_path,
        FIXTURES / "termidy-ethical-ai.html",
        fetched_at="2026-01-02T03:04:05Z",
        converter="trafilatura 2.0 via crawl4ai 0.9",
        publisher="termidy",
    )

    frontmatter, _ = read_version(path)
    assert frontmatter["converter"] == "trafilatura 2.0 via crawl4ai 0.9"
    assert frontmatter["publisher"] == "termidy"


def test_ageing_rewrites_only_fetched_at_and_reads_publisher_values_as_strings(
    tmp_path: Path,
) -> None:
    by_hand = tmp_path / "learn.microsoft.com--en-us-azure-foundry-what-is-foundry--0badc0de.md"
    by_hand.write_text(
        "---\n"
        "url: https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry\n"
        "fetched_at: 2026-10-01T08:00:00Z\n"
        "sha256: 0badc0de\n"
        "publisher: microsoft\n"
        "authority: primary\n"
        "converter: md-twin\n"
        "etag: '\"RYzzG3LLzfqUX6b79i4xKDnTE/w=\"'\n"
        "modified: 2026-08-13T00:00:00.0000000Z\n"
        "original:\n"
        "  url: https://learn.microsoft.com/x?accept=text/markdown\n"
        "  stored: false\n"
        "---\n"
        "# What is Microsoft Foundry?\n"
    )

    age_version(by_hand, days=40)

    frontmatter, body = read_version(by_hand)
    fetched_at = datetime.fromisoformat(frontmatter["fetched_at"])
    assert abs(datetime.now(UTC) - timedelta(days=40) - fetched_at) < timedelta(minutes=1)
    assert frontmatter["modified"] == "2026-08-13T00:00:00.0000000Z"
    assert frontmatter["etag"] == '"RYzzG3LLzfqUX6b79i4xKDnTE/w="'
    assert '"\\"RYzzG3LLzfqUX6b79i4xKDnTE/w=\\""' in by_hand.read_text()
    assert frontmatter["original"] == {
        "url": "https://learn.microsoft.com/x?accept=text/markdown",
        "stored": "false",
    }
    assert body == b"# What is Microsoft Foundry?\n"
