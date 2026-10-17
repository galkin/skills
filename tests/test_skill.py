import argparse
import json
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from lorekeep import cli
from lorekeep.commands.skill import skill_folder
from tests.support import edges_over, get, lorekeep, make_store, run_cli

# A command section of SKILL.md or references/owner.md is headed "## `lorekeep <command>`"; each
# flag it documents is a bullet that starts with the flag in backticks. Any other flag the text
# names starts a code span (`--max-age 0`), and must exist too.
SECTION = re.compile(r"`lorekeep ([a-z ]+)`")
DOCUMENTED_FLAG = re.compile(r"^- `(--[a-z][a-z-]*)", re.MULTILINE)
MENTIONED_FLAG = re.compile(r"`(--[a-z][a-z-]*)")
# In `--help`, an option starts its line after two spaces; a subcommand after four.
HELP_FLAG = re.compile(r"^  (?:-\w, )?(--[a-z][a-z-]*)", re.MULTILINE)
HELP_SUBCOMMAND = re.compile(r"^    ([a-z][a-z-]*)\s", re.MULTILINE)
# What a Run calls is in SKILL.md; the owner's commands are in references/owner.md.
RUN_COMMANDS = {"get", "add", "search", "status"}
MAX_SKILL_LINES = 250
GUARDRAILS = (
    "https://docs.nvidia.com/nemo/guardrails/latest/configure-guardrails/guardrail-catalog/"
    "jailbreak-protection"
)


def skill_frontmatter(text: str) -> dict[str, str]:
    _, head, _ = text.split("---\n", 2)
    return yaml.safe_load(head)


def owner_reference() -> str:
    return skill_folder().joinpath("references", "owner.md").read_text(encoding="utf-8")


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


def drift(skill: str, owner: str) -> list[str]:
    """What SKILL.md and references/owner.md disagree with the parser on, one line each; empty
    when they agree. Every command has one section in one of the two files, documenting every
    flag of its `--help` as a bullet; every flag either file names exists."""
    in_parser = parsed()
    every_flag = set().union(*in_parser.values()) | {"--version"}
    in_docs: dict[str, tuple[str, str]] = {}
    lines: list[str] = []
    for file, text in (("SKILL.md", skill), ("owner.md", owner)):
        for name, body in sections(text).items():
            if name in in_docs:
                lines.append(f"{name}: a section in both SKILL.md and owner.md")
            in_docs[name] = (file, body)
        lines += [
            f"{file}: {flag} not in any --help"
            for flag in set(MENTIONED_FLAG.findall(outside_sections(text))) - every_flag
        ]
    lines += [f"{name}: no section in SKILL.md or owner.md" for name in in_parser.keys() - in_docs]
    lines += [f"{name}: no such command" for name in in_docs.keys() - in_parser.keys()]
    for name in in_parser.keys() & in_docs.keys():
        file, body = in_docs[name]
        bullets = set(DOCUMENTED_FLAG.findall(body))
        named = bullets | set(MENTIONED_FLAG.findall(body))
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
    skill = run_cli(["skill"]).stdout

    assert parsed().keys() >= {"get", "add", "search", "status", "tag add", "skill"}
    assert drift(skill, owner_reference()) == []


def test_skill_md_covers_what_a_run_calls_and_owner_md_the_rest() -> None:
    skill = run_cli(["skill"]).stdout

    assert sections(skill).keys() == RUN_COMMANDS
    assert sections(owner_reference()).keys() == parsed().keys() - RUN_COMMANDS


def test_skill_md_is_under_250_lines() -> None:
    assert len(run_cli(["skill"]).stdout.splitlines()) < MAX_SKILL_LINES


def json_examples(skill: str) -> list[dict[str, Any]]:
    return [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", skill, re.DOTALL)]


def test_the_json_examples_have_the_fields_the_commands_print(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    edges, _ = edges_over(
        "helm-rollback.v3-redirect", "helm-rollback.html", "guardrails-jailbreak-protection.twin"
    )
    got = json.loads(
        get(store, edges, "--json", "https://v3.helm.sh/docs/helm/helm_rollback/").stdout
    )
    get(store, edges, GUARDRAILS, tag="nvidia")
    found = json.loads(lorekeep(store, edges, "search", "--json", "--exact", "threshold").stdout)
    status = json.loads(lorekeep(store, edges, "status", "--json").stdout)

    examples = json_examples(run_cli(["skill"]).stdout)

    assert [example.keys() for example in examples] == [
        got.keys(),
        got.keys(),
        found.keys(),
        status.keys(),
    ]
    assert [result.keys() for result in examples[2]["results"]] == [
        result.keys() for result in found["results"]
    ][:1]


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


def test_a_flag_added_to_the_parser_alone_is_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    skill = run_cli(["skill"]).stdout
    monkeypatch.setattr(cli, "build_parser", with_extra_flag("search", "--fuzzy"))

    assert drift(skill, owner_reference()) == ["search: --fuzzy not in SKILL.md"]


def test_a_flag_documented_in_the_owner_reference_alone_is_drift() -> None:
    skill = run_cli(["skill"]).stdout
    edited = owner_reference().replace(
        "## `lorekeep index`\n", "## `lorekeep index`\n\n- `--quick` faster\n"
    )

    assert drift(skill, edited) == ["index: --quick not in --help"]


def test_a_flag_named_in_the_text_alone_is_drift() -> None:
    skill = run_cli(["skill"]).stdout
    in_section = skill.replace("ask the publisher now", "ask the publisher now (`--retry 2`)")
    outside = skill.replace("## How a Run works\n", "## How a Run works\n\nUse `--quiet`.\n")

    assert drift(in_section, owner_reference()) == ["get: --retry not in --help"]
    assert drift(outside, owner_reference()) == ["SKILL.md: --quiet not in any --help"]


def test_a_command_without_a_section_is_drift() -> None:
    skill = run_cli(["skill"]).stdout
    edited = owner_reference().replace("## `lorekeep restore`", "## Restoring")

    assert drift(skill, edited) == ["restore: no section in SKILL.md or owner.md"]


def installed(repo: Path) -> Path:
    return repo / ".agents" / "skills" / "lorekeep"


def test_install_copies_the_skill_folder_into_the_repo_and_reminds_of_the_lock(
    tmp_path: Path,
) -> None:
    printed = run_cli(["skill"]).stdout

    result = run_cli(["skill", "--install", str(tmp_path)])

    assert result.exit_code == 0
    folder = installed(tmp_path)
    assert (folder / "SKILL.md").read_text() == printed
    assert (folder / "references" / "store.md").read_text().startswith("# The Store")
    assert (folder / "references" / "owner.md").read_text() == owner_reference()
    assert str(folder) in result.stdout
    assert "skill lock" in result.stdout.splitlines()[-1]
    assert "hash" in result.stdout.splitlines()[-1]


def test_install_names_the_repos_skills_lock_when_it_keeps_one(tmp_path: Path) -> None:
    (tmp_path / "skills-lock.json").write_text('{"version": 1, "skills": {}}\n')

    result = run_cli(["skill", "--install", str(tmp_path)])

    assert result.exit_code == 0
    assert "skills-lock.json" in result.stdout.splitlines()[-1]
    assert (tmp_path / "skills-lock.json").read_text() == '{"version": 1, "skills": {}}\n'


def test_a_second_install_exits_non_zero_and_changes_nothing(tmp_path: Path) -> None:
    run_cli(["skill", "--install", str(tmp_path)])
    skill = installed(tmp_path) / "SKILL.md"
    skill.write_text("edited by hand\n")
    (installed(tmp_path) / "local.md").write_text("kept\n")

    result = run_cli(["skill", "--install", str(tmp_path)])

    assert result.exit_code != 0
    assert "--force" in result.stderr
    assert skill.read_text() == "edited by hand\n"
    assert (installed(tmp_path) / "local.md").read_text() == "kept\n"


def test_install_with_force_replaces_the_installed_folder(tmp_path: Path) -> None:
    run_cli(["skill", "--install", str(tmp_path)])
    (installed(tmp_path) / "SKILL.md").write_text("edited by hand\n")
    (installed(tmp_path) / "local.md").write_text("stale\n")

    result = run_cli(["skill", "--install", str(tmp_path), "--force"])

    assert result.exit_code == 0
    assert (installed(tmp_path) / "SKILL.md").read_text() == run_cli(["skill"]).stdout
    assert not (installed(tmp_path) / "local.md").exists()
    assert (installed(tmp_path) / "references" / "store.md").is_file()


def test_an_install_that_fails_half_way_leaves_no_staging_folder_and_the_old_copy_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert run_cli(["skill", "--install", str(tmp_path)]).exit_code == 0
    before = (installed(tmp_path) / "SKILL.md").read_bytes()
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

    result = run_cli(["skill", "--install", str(tmp_path), "--force"])

    assert result.exit_code == 1
    assert result.stderr.startswith("lorekeep: error: ")
    assert "No space left on device" in result.stderr
    assert sorted(path.name for path in installed(tmp_path).parent.iterdir()) == ["lorekeep"]
    assert (installed(tmp_path) / "SKILL.md").read_bytes() == before


def test_install_into_a_repo_that_does_not_exist_is_an_error_and_creates_nothing(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "nowhere"

    result = run_cli(["skill", "--install", str(missing)])

    assert result.exit_code != 0
    assert str(missing) in result.stderr
    assert not missing.exists()


def test_force_without_install_is_a_usage_error() -> None:
    result = run_cli(["skill", "--force"])

    assert result.exit_code == 2
    assert "--install" in result.stderr
    assert result.stdout == ""
