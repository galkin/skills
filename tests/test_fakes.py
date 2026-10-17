"""The fakes at the seam's edge behave as `tests/fixtures/README.md` says."""

from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path

import httpx
import pytest

from lorekeep.edges import CommandResult, Edges, FetcherNotInstalled, RenderedPage
from tests.support import FIXTURES, FakeFetcher, FakeRunner, FakeTransport, run_cli, status_in_child

ANTHROPIC_TWIN = "https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md"


def client(transport: FakeTransport) -> httpx.Client:
    return httpx.Client(transport=transport, follow_redirects=True)


def test_a_percent_encoded_query_finds_the_fixture_recorded_decoded() -> None:
    transport = FakeTransport.from_fixtures()

    response = client(transport).get(
        "https://learn.microsoft.com/en-us/azure/foundry/what-is-foundry?accept=text%2Fmarkdown"
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert transport.misses == []


def test_redirects_are_served_from_their_fixtures() -> None:
    transport = FakeTransport.from_fixtures()

    response = client(transport).get(
        "https://learn.microsoft.com/en-us/azure/ai-foundry/what-is-azure-ai-foundry?accept=text/markdown"
    )

    assert response.status_code == 200
    assert len(transport.requests) == 3
    assert [r.status_code for r in response.history] == [301, 301]


def test_the_fixture_with_most_matching_headers_wins() -> None:
    transport = FakeTransport.from_fixtures()
    http = client(transport)

    conditional = http.get(ANTHROPIC_TWIN, headers={"If-None-Match": '"a1-twin"'})
    plain = http.get(ANTHROPIC_TWIN)
    other_etag = http.get(ANTHROPIC_TWIN, headers={"If-None-Match": '"other"'})

    assert conditional.status_code == 304
    assert plain.status_code == 200
    assert plain.text.startswith((FIXTURES / "anthropic-prompt-caching.twin/body.md").read_text())
    assert other_etag.status_code == 200


def test_the_host_is_compared_lower_cased() -> None:
    transport = FakeTransport.from_fixtures()

    response = client(transport).get(ANTHROPIC_TWIN.replace("platform", "PLATFORM"))

    assert response.status_code == 200


def test_an_error_fixture_raises_its_exception() -> None:
    transport = FakeTransport.from_fixtures()

    with pytest.raises(httpx.ReadTimeout):
        client(transport).get("https://example.test/slow")
    assert len(transport.requests) == 1


def test_an_unknown_url_is_404_and_a_recorded_miss() -> None:
    transport = FakeTransport.from_fixtures()

    response = client(transport).get("https://example.test/nothing-here")

    assert response.status_code == 404
    assert transport.misses == ["https://example.test/nothing-here"]
    assert [str(r.url) for r in transport.requests] == ["https://example.test/nothing-here"]


def test_a_transport_serves_only_the_folders_it_was_built_from() -> None:
    transport = FakeTransport([FIXTURES / "termidy-coordinator-and-subagents.noisy"])
    url = "https://claude.termidy.com/learn/ccar-f/agentic-architecture/coordinator-and-subagents/"

    body = client(transport).get(url).content

    assert body == (FIXTURES / "termidy-coordinator-and-subagents.noisy/body.html").read_bytes()
    assert client(transport).get(ANTHROPIC_TWIN).status_code == 404


def test_the_fetcher_returns_its_page_and_records_the_call(tmp_path: Path) -> None:
    page = tmp_path / "rendered.html"
    page.write_text("<html><body><nav>menu</nav><p>text</p></body></html>")
    fetcher = FakeFetcher({"https://milvus.io/docs/overview.md": (page, "https://milvus.io/docs")})

    rendered = fetcher.fetch("https://milvus.io/docs/overview.md")

    assert rendered == RenderedPage(html=page.read_text(), final_url="https://milvus.io/docs")
    assert fetcher.calls == ["https://milvus.io/docs/overview.md"]


def test_the_fetcher_not_installed_says_so_and_records_no_call(tmp_path: Path) -> None:
    fetcher = FakeFetcher({}, installed=False)

    with pytest.raises(FetcherNotInstalled) as raised:
        fetcher.fetch("https://milvus.io/docs/overview.md")

    assert "lorekeep[browser]" in str(raised.value)
    assert fetcher.calls == []


def test_the_runner_records_commands_and_returns_canned_results() -> None:
    runner = FakeRunner([(1, "", "denied")])

    first = runner.run(["gcloud", "storage", "cp", "a", "gs://b/"])
    second = runner.run(["gcloud", "storage", "rsync", "a", "gs://b/"])

    assert first == CommandResult(returncode=1, stdout="", stderr="denied")
    assert second == CommandResult(returncode=0, stdout="", stderr="")
    assert runner.calls == [
        ["gcloud", "storage", "cp", "a", "gs://b/"],
        ["gcloud", "storage", "rsync", "a", "gs://b/"],
    ]


def test_a_command_runs_with_the_three_fakes(tmp_path: Path) -> None:
    edges = Edges(
        transport=FakeTransport.from_fixtures(),
        fetcher=FakeFetcher({}, installed=False),
        runner=FakeRunner(),
    )

    result = run_cli(["status", "--store", str(tmp_path)], edges=edges)

    assert result.exit_code == 0
    # The only line on stderr is the note that `status` built the missing Index (ticket 12).
    assert [line for line in result.stderr.splitlines() if "rebuilt" not in line] == []
    assert "0 Versions" in result.stdout


def test_a_child_process_builds_its_own_fakes(tmp_path: Path) -> None:
    with ProcessPoolExecutor(max_workers=1, mp_context=get_context("spawn")) as pool:
        result = pool.submit(status_in_child, str(tmp_path)).result()

    assert result.exit_code == 0
    assert "0 Versions" in result.stdout
