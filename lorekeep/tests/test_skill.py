import argparse
import json
import re
import shlex
import shutil
from collections.abc import Callable
from importlib import metadata
from pathlib import Path
from typing import Any

import pytest
import yaml

from lorekeep import cli
from lorekeep.commands import skill as skill_command
from lorekeep.commands.skill import entry_point, skill_folder
from tests.support import edges_over, get, lorekeep, make_store, run_cli

# A command section of a skill file is headed "## `lorekeep <command>`". A Run's commands are in
# the files a Reader or a Collector reads, whose flags `--help` lists (SKILL.md says so); the
# owner's are in references/curating.md, which documents each flag as a bullet that starts with
# the flag in backticks. Any other flag the text names starts a code span (`--max-age 0`), and must
# exist too.
SECTION = re.compile(r"`lorekeep ([a-z ]+)`")
DOCUMENTED_FLAG = re.compile(r"^- `(--[a-z][a-z-]*)", re.MULTILINE)
MENTIONED_FLAG = re.compile(r"`(--[a-z][a-z-]*)")
# In `--help`, an option starts its line after two spaces; a subcommand after four.
HELP_FLAG = re.compile(r"^  (?:-\w, )?(--[a-z][a-z-]*)", re.MULTILINE)
HELP_SUBCOMMAND = re.compile(r"^    ([a-z][a-z-]*)\s", re.MULTILINE)
RUN_FILES = ("SKILL.md", "references/reading.md", "references/collecting.md")
OWNER_FILE = "references/curating.md"
RUN_COMMANDS = {"get", "add", "search", "status"}
MAX_SKILL_LINES = 250
GUARDRAILS = (
    "https://docs.nvidia.com/nemo/guardrails/latest/configure-guardrails/guardrail-catalog/"
    "jailbreak-protection"
)
SELF_CHECK = (
    "https://docs.nvidia.com/nemo/guardrails/configure-guardrails/guardrail-catalog/self-check"
)
# A host no rule knows, asked with a fragment: the address of the `get --json` example.
HELM = "https://helm.sh/docs/helm/helm_rollback/#synopsis"
# An example block: a `$ lorekeep …` line, then what the command printed, up to the next one.
EXAMPLE = re.compile(r"^\$ lorekeep (.+)\n((?:(?!\$ |```).*\n)*)", re.MULTILINE)
# What changes from one run to the next: the Store's folder and the time of the fetch.
STORE_PATH = re.compile(r"/[^\s\"]*/store/")
TIMES = {"fetched_at", "verified_at"}


def skill_frontmatter(text: str) -> dict[str, str]:
    _, head, _ = text.split("---\n", 2)
    return yaml.safe_load(head)


def skill_file(name: str) -> str:
    return skill_folder().joinpath(*name.split("/")).read_text(encoding="utf-8")


def skill_files() -> dict[str, str]:
    """Every file a command section can be in, by its path in the skill folder."""
    return {name: skill_file(name) for name in (*RUN_FILES, OWNER_FILE)}


def sections(text: str) -> dict[str, str]:
    """Every command section of a skill file with its body."""
    found: dict[str, str] = {}
    for chunk in text.split("\n## ")[1:]:
        heading, _, body = chunk.partition("\n")
        command = SECTION.fullmatch(heading)
        if command:
            found[command.group(1)] = body
    return found


def outside_sections(text: str) -> str:
    """The text of a skill file that belongs to no command section."""
    chunks = text.split("\n## ")
    return "\n".join(
        chunks[:1]
        + [chunk for chunk in chunks[1:] if not SECTION.fullmatch(chunk.partition("\n")[0])]
    )


def parsed(command: tuple[str, ...] = ()) -> dict[str, set[str]]:
    """Every leaf command of the parser with the flags its `--help` lists, `--help` aside."""
    help_text = run_cli([*command, "--help"]).stdout
    subcommands = HELP_SUBCOMMAND.findall(help_text)
    if not subcommands:
        return {" ".join(command): set(HELP_FLAG.findall(help_text)) - {"--help"}}
    commands: dict[str, set[str]] = {}
    for name in subcommands:
        commands |= parsed((*command, name))
    return commands


def drift(files: dict[str, str]) -> list[str]:
    """What the skill's files disagree with the parser on, one line each; empty when they agree.
    Every command has one section in one file; the owner's file documents every flag of its
    `--help` as a bullet; every flag any file names exists."""
    in_parser = parsed()
    every_flag = set().union(*in_parser.values()) | {"--version"}
    in_docs: dict[str, tuple[str, str]] = {}
    lines: list[str] = []
    for file, text in files.items():
        for name, body in sections(text).items():
            if name in in_docs:
                lines.append(f"{name}: a section in both {in_docs[name][0]} and {file}")
            in_docs[name] = (file, body)
        lines += [
            f"{file}: {flag} not in any --help"
            for flag in set(MENTIONED_FLAG.findall(outside_sections(text))) - every_flag
        ]
    lines += [f"{name}: no section in the skill" for name in in_parser.keys() - in_docs]
    lines += [f"{name}: no such command" for name in in_docs.keys() - in_parser.keys()]
    for name in in_parser.keys() & in_docs.keys():
        file, body = in_docs[name]
        bullets = set(DOCUMENTED_FLAG.findall(body))
        named = bullets | set(MENTIONED_FLAG.findall(body))
        if file == OWNER_FILE:
            lines += [f"{name}: {flag} not in {file}" for flag in in_parser[name] - bullets]
        lines += [f"{name}: {flag} not in --help" for flag in named - in_parser[name]]
    return sorted(set(lines))


def test_skill_prints_the_skill_with_its_name_and_description() -> None:
    result = run_cli(["skill"])

    assert result.exit_code == 0
    assert result.stdout.startswith("---\n")
    head = skill_frontmatter(result.stdout)
    assert head["name"] == "lorekeep"
    assert "lorekeep" in head["description"]


def test_every_command_and_flag_of_the_parser_is_in_the_skill_and_no_other() -> None:
    assert parsed().keys() >= {"get", "add", "search", "status", "tag add", "skill"}
    assert drift(skill_files()) == []


def test_the_run_files_cover_what_a_run_calls_and_the_owner_file_the_rest() -> None:
    files = skill_files()
    in_run_files = [sections(files[name]).keys() for name in RUN_FILES]

    assert set().union(*in_run_files) == RUN_COMMANDS
    assert sections(files[OWNER_FILE]).keys() == parsed().keys() - RUN_COMMANDS


def test_skill_md_links_every_reference() -> None:
    skill = run_cli(["skill"]).stdout
    references = {path.name for path in skill_folder().joinpath("references").iterdir()}

    assert {name for name in references if f"](references/{name})" in skill} == references


def test_skill_md_is_under_250_lines() -> None:
    assert len(run_cli(["skill"]).stdout.splitlines()) < MAX_SKILL_LINES


def json_examples(text: str) -> list[dict[str, Any]]:
    return [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", text, re.DOTALL)]


def test_the_json_examples_have_the_fields_the_commands_print(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("helm-rollback.html", "guardrails-jailbreak-protection.twin")
    got = json.loads(get(store, edges, "--json", HELM).stdout)
    get(store, edges, GUARDRAILS, tag="nvidia")
    found = json.loads(lorekeep(store, edges, "search", "--json", "--exact", "threshold").stdout)
    status = json.loads(lorekeep(store, edges, "status", "--json").stdout)

    examples = json_examples(
        skill_file("references/reading.md") + skill_file("references/store.md")
    )

    assert [example.keys() for example in examples] == [got.keys(), found.keys(), status.keys()]
    assert [result.keys() for result in examples[1]["results"]] == [
        result.keys() for result in found["results"]
    ][:1]


def examples_of(text: str, command: str) -> list[tuple[list[str], str]]:
    """Every `$ lorekeep <command> …` example of a skill file: its arguments and what it printed."""
    return [
        (shlex.split(argv), printed)
        for argv, printed in EXAMPLE.findall(text)
        if argv.split()[0] == command
    ]


def as_printed(text: str) -> str:
    return STORE_PATH.sub("/…/store/", text)


def test_the_get_example_is_what_get_prints_for_a_host_no_rule_knows(tmp_path: Path) -> None:
    reading = skill_file("references/reading.md")
    [(argv, stderr)] = examples_of(reading, "get")
    edges, transport = edges_over("helm-rollback.html")

    result = lorekeep(make_store(tmp_path), edges, *argv, tag="nvidia")

    assert argv == ["get", "--json", HELM]
    assert transport.misses == []
    assert result.stderr == stderr
    printed, example = json.loads(as_printed(result.stdout)), json_examples(reading)[0]
    assert printed.keys() == example.keys() >= TIMES
    assert {key: value for key, value in printed.items() if key not in TIMES} == {
        key: value for key, value in example.items() if key not in TIMES
    }
    assert printed["authority"] == "third-party"


def test_the_search_examples_are_what_search_prints(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over("guardrails-jailbreak-protection.twin", "guardrails-self-check.html")
    get(store, edges, GUARDRAILS, tag="nvidia")
    get(store, edges, SELF_CHECK, tag="nvidia")
    examples = examples_of(skill_file("references/reading.md"), "search")

    results = [lorekeep(store, edges, *argv, tag="nvidia") for argv, _ in examples]

    assert len(examples) >= 3
    # A `lorekeep: note:` line of an example is stderr; the rest is stdout.
    for result, (_, shown) in zip(results, examples, strict=True):
        notes = [line for line in shown.splitlines() if line.startswith("lorekeep: note: ")]
        assert set(notes) <= set(result.stderr.splitlines())
        assert as_printed(result.stdout).splitlines() == [
            line for line in shown.splitlines() if line not in notes
        ]


def with_extra_flag(command: str, flag: str) -> Callable[[], argparse.ArgumentParser]:
    """`build_parser` with one more flag on one command, as a change to the parser alone."""
    build = cli.build_parser

    def build_with_flag() -> argparse.ArgumentParser:
        parser = build()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                action.choices[command].add_argument(flag, action="store_true")
        return parser

    return build_with_flag


def test_a_flag_added_to_an_owner_command_alone_is_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "build_parser", with_extra_flag("index", "--fuzzy"))

    assert drift(skill_files()) == ["index: --fuzzy not in references/curating.md"]


def test_a_flag_added_to_a_run_command_is_left_to_its_help(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "build_parser", with_extra_flag("search", "--fuzzy"))

    assert drift(skill_files()) == []


def test_a_flag_documented_in_the_owner_file_alone_is_drift() -> None:
    files = skill_files()
    files[OWNER_FILE] = files[OWNER_FILE].replace(
        "## `lorekeep index`\n", "## `lorekeep index`\n\n- `--quick` faster\n"
    )

    assert drift(files) == ["index: --quick not in --help"]


def test_a_flag_named_in_the_text_alone_is_drift() -> None:
    in_section, outside = skill_files(), skill_files()
    reading = in_section["references/reading.md"]
    in_section["references/reading.md"] = reading.replace("(`--max-age 0`)", "(`--retry 2`)")
    outside["SKILL.md"] = outside["SKILL.md"].replace(
        "## Before you start\n", "## Before you start\n\nUse `--quiet`.\n"
    )

    assert drift(in_section) == ["get: --retry not in --help"]
    assert drift(outside) == ["SKILL.md: --quiet not in any --help"]


def test_a_command_without_a_section_is_drift() -> None:
    files = skill_files()
    files[OWNER_FILE] = files[OWNER_FILE].replace("## `lorekeep restore`", "## Restoring")

    assert drift(files) == ["restore: no section in the skill"]


COMMIT = "a32219fd68e06afbb372ce3491786ff343d6eadd"


def test_build_writes_the_skill_its_references_and_an_entry_point_pinned_to_the_commit(
    tmp_path: Path,
) -> None:
    target = tmp_path / "lorekeep"

    result = run_cli(["skill", "--build", str(target), "--rev", COMMIT])

    assert result.exit_code == 0
    assert (target / "SKILL.md").read_text() == run_cli(["skill"]).stdout
    assert (target / "references" / "store.md").read_text().startswith("# The Store")
    for name in ("reading.md", "collecting.md", "curating.md"):
        assert (target / "references" / name).read_text() == skill_file(f"references/{name}")
    script = target / "bin" / "lorekeep"
    assert script.stat().st_mode & 0o111 == 0o111
    version = metadata.version("lorekeep")
    python = metadata.metadata("lorekeep")["Requires-Python"]
    assert script.read_text() == entry_point(version, COMMIT, python)
    assert f'--python "{python}"' in script.read_text()
    assert (
        f'--from "lorekeep[browser] @ git+https://github.com/galkin/skills@{COMMIT}'
        '#subdirectory=lorekeep"' in script.read_text()
    )
    assert f"lorekeep-v{version}" in result.stdout


def test_build_pins_the_commit_the_release_tag_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(skill_command, "release_commit", lambda version: COMMIT)

    result = run_cli(["skill", "--build", str(tmp_path / "lorekeep")])

    assert result.exit_code == 0, result.stderr
    assert f"@{COMMIT}#" in (tmp_path / "lorekeep" / "bin" / "lorekeep").read_text()


def test_build_without_the_release_tag_or_a_full_hash_is_an_error_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(skill_command, "release_commit", lambda version: None)

    untagged = run_cli(["skill", "--build", str(tmp_path / "lorekeep")])
    short = run_cli(["skill", "--build", str(tmp_path / "lorekeep"), "--rev", "a32219f"])

    assert (untagged.exit_code, short.exit_code) == (2, 2)
    assert "tag it first" in untagged.stderr
    assert not (tmp_path / "lorekeep").exists()


def test_build_replaces_what_the_folder_held(tmp_path: Path) -> None:
    target = tmp_path / "lorekeep"
    target.mkdir()
    (target / "SKILL.md").write_text("edited by hand\n")
    (target / "stale.md").write_text("stale\n")

    result = run_cli(["skill", "--build", str(target), "--rev", COMMIT])

    assert result.exit_code == 0
    assert (target / "SKILL.md").read_text() == run_cli(["skill"]).stdout
    assert not (target / "stale.md").exists()


def test_a_build_that_fails_half_way_leaves_no_staging_folder_and_the_old_copy_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "lorekeep"
    assert run_cli(["skill", "--build", str(target), "--rev", COMMIT]).exit_code == 0
    before = (target / "SKILL.md").read_bytes()
    copytree = shutil.copytree
    depth = 0

    def copy_then_fail(*args: object, **kwargs: object) -> object:
        """The staging folder is written in full (copytree recurses through this name), then
        the copy fails the way a full disk would."""
        nonlocal depth
        depth += 1
        try:
            result = copytree(*args, **kwargs)  # type: ignore[arg-type]
        finally:
            depth -= 1
        if depth == 0:
            raise OSError("No space left on device")
        return result

    monkeypatch.setattr(shutil, "copytree", copy_then_fail)

    result = run_cli(["skill", "--build", str(target), "--rev", COMMIT])

    assert result.exit_code == 1
    assert result.stderr.startswith("lorekeep: error: ")
    assert "No space left on device" in result.stderr
    assert sorted(path.name for path in tmp_path.iterdir()) == ["lorekeep"]
    assert (target / "SKILL.md").read_bytes() == before


def test_build_into_a_folder_that_does_not_exist_is_an_error_and_creates_nothing(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "nowhere" / "lorekeep"

    result = run_cli(["skill", "--build", str(missing), "--rev", COMMIT])

    assert result.exit_code == 2
    assert str(missing.parent) in result.stderr
    assert not missing.parent.exists()
