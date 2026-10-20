"""`lorekeep.toml` over the package's default host table, as `status` reports it."""

from pathlib import Path

from tests.support import run_cli

DEFAULT_RULES = [
    ["platform.claude.com/", "anthropic", "primary", "twin=md-suffix"],
    ["docs.aws.amazon.com/", "aws", "primary", "twin=md-suffix", "page_suffix=.html"],
    ["learn.microsoft.com/", "microsoft", "primary", "twin=accept-header"],
    ["docs.nvidia.com/", "nvidia", "primary"],
    ["docs.nvidia.com/cuvs/", "nvidia", "primary", "twin=md-suffix"],
    ["docs.nvidia.com/dynamo/", "nvidia", "primary", "twin=md-suffix"],
    ["docs.nvidia.com/nemo/curator/", "nvidia", "primary", "twin=md-suffix"],
    ["docs.nvidia.com/nemo/guardrails/", "nvidia", "primary", "twin=md-suffix"],
    ["docs.nvidia.com/nemo/gym/", "nvidia", "primary", "twin=md-suffix"],
    ["docs.nvidia.com/openshell/", "nvidia", "primary", "twin=md-suffix"],
    ["docs.langchain.com/", "langchain", "primary", "twin=md-suffix"],
    ["cloud.google.com/", "google", "primary"],
    ["milvus.io/", "milvus", "primary"],
    ["claude.termidy.com/", "termidy", "third-party"],
    ["raw.githubusercontent.com/", "github", "third-party", "twin=raw"],
    ["github.com/", "github", "third-party", "twin=github-raw"],
]


def host_rules(stdout: str) -> list[list[str]]:
    """The rows `status` prints under `Host rules`, one list of words per rule."""
    lines = stdout.split("Host rules")[1].splitlines()[1:]
    return [line.split() for line in lines if line.startswith("  ")]


def status(store: Path) -> str:
    result = run_cli(["status", "--rules", "--store", str(store)])
    assert result.exit_code == 0, result.stderr
    return result.stdout


def test_without_lorekeep_toml_the_default_table_and_defaults_apply(tmp_path: Path) -> None:
    stdout = status(tmp_path)

    assert host_rules(stdout) == DEFAULT_RULES
    assert "Freshness window: 30 days" in stdout
    assert "Bucket: none" in stdout


def test_lorekeep_toml_overrides_a_default_rule_in_place_and_extends_the_table(
    tmp_path: Path,
) -> None:
    (tmp_path / "lorekeep.toml").write_text(
        """\
bucket = "agentic-system-design-sources"
freshness_days = 7

[[hosts]]
prefix = "raw.githubusercontent.com/anthropics/"
publisher = "anthropic"
authority = "primary"
twin = "raw"

[[hosts]]
prefix = "learn.microsoft.com/"
publisher = "microsoft-learn"
authority = "official"

[[hosts]]
prefix = "example.test/app/"
publisher = "example"
authority = "third-party"
browser = true
cut = ["nav", ".cookie-banner"]
"""
    )

    stdout = status(tmp_path)

    expected = [list(rule) for rule in DEFAULT_RULES]
    expected[2] = ["learn.microsoft.com/", "microsoft-learn", "official", "(lorekeep.toml)"]
    own = "(lorekeep.toml)"
    expected += [
        ["raw.githubusercontent.com/anthropics/", "anthropic", "primary", "twin=raw", own],
        ["example.test/app/", "example", "third-party", "browser", "cut=nav,.cookie-banner", own],
    ]
    assert host_rules(stdout) == expected
    assert "Freshness window: 7 days" in stdout
    assert "Bucket: agentic-system-design-sources" in stdout


def test_lorekeep_toml_with_only_some_keys_takes_the_defaults_for_the_rest(tmp_path: Path) -> None:
    (tmp_path / "lorekeep.toml").write_text('bucket = "b"\n')

    stdout = status(tmp_path)

    assert "Freshness window: 30 days" in stdout
    assert host_rules(stdout) == DEFAULT_RULES


def test_a_malformed_lorekeep_toml_names_the_key_that_failed(tmp_path: Path) -> None:
    rule = '[[hosts]]\nprefix = "a.test/"\npublisher = "a"\nauthority = "primary"\n'
    cases = {
        'freshness_days = "soon"\n': "freshness_days",
        "freshness_days = -1\n": "freshness_days",
        "bucket = 3\n": "bucket",
        'colour = "red"\n': "colour",
        'hosts = "all"\n': "hosts",
        rule + '[[hosts]]\nprefix = "b.test/"\nauthority = "primary"\n': "hosts[2].publisher",
        rule.replace('"primary"', '"trusted"'): "hosts[1].authority",
        rule + 'twin = "pdf"\n': "hosts[1].twin",
        rule + "browser = 1\n": "hosts[1].browser",
        rule + 'cut = "nav"\n': "hosts[1].cut",
        rule + "page_suffix = 3\n": "hosts[1].page_suffix",
        rule + 'twinn = "raw"\n': "hosts[1].twinn",
        "bucket = \n": "lorekeep.toml",
    }
    for text, key in cases.items():
        (tmp_path / "lorekeep.toml").write_text(text)

        result = run_cli(["status", "--rules", "--store", str(tmp_path)])

        assert result.exit_code != 0, text
        assert key in result.stderr, (text, result.stderr)
        assert len(result.stderr.strip().splitlines()) == 1, text
