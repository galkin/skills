import argparse
import re
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from lorekeep import cli
from tests.support import run_cli

# A command section of SKILL.md is headed "## `lorekeep <command>`"; each flag it documents is a
# bullet that starts with the flag in backticks.
SECTION = re.compile(r"`lorekeep ([a-z ]+)`")
DOCUMENTED_FLAG = re.compile(r"^- `(--[a-z][a-z-]*)", re.MULTILINE)
# In `--help`, an option starts its line after two spaces; a subcommand after four.
HELP_FLAG = re.compile(r"^  (?:-\w, )?(--[a-z][a-z-]*)", re.MULTILINE)
HELP_SUBCOMMAND = re.compile(r"^    ([a-z][a-z-]*)\s", re.MULTILINE)


def skill_frontmatter(text: str) -> dict[str, str]:
    _, head, _ = text.split("---\n", 2)
    return yaml.safe_load(head)


def documented(skill: str) -> dict[str, set[str]]:
    """Every command section of SKILL.md with the flags it documents."""
    sections: dict[str, set[str]] = {}
    for chunk in skill.split("\n## ")[1:]:
        heading, _, body = chunk.partition("\n")
        command = SECTION.fullmatch(heading)
        if command:
            sections[command.group(1)] = set(DOCUMENTED_FLAG.findall(body))
    return sections


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


def drift(skill: str) -> list[str]:
    """What SKILL.md and the parser disagree on, one line each; empty when they agree."""
    in_skill, in_parser = documented(skill), parsed()
    lines = [f"{name}: no section in SKILL.md" for name in in_parser.keys() - in_skill.keys()]
    lines += [f"{name}: no such command" for name in in_skill.keys() - in_parser.keys()]
    for name in in_parser.keys() & in_skill.keys():
        lines += [f"{name}: {flag} not in SKILL.md" for flag in in_parser[name] - in_skill[name]]
        lines += [f"{name}: {flag} not in --help" for flag in in_skill[name] - in_parser[name]]
    return sorted(lines)


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
    assert drift(skill) == []


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

    assert drift(skill) == ["search: --fuzzy not in SKILL.md"]


def test_a_flag_documented_in_the_skill_alone_is_drift() -> None:
    skill = run_cli(["skill"]).stdout
    edited = skill.replace("## `lorekeep index`\n", "## `lorekeep index`\n\n- `--quick` faster\n")

    assert drift(edited) == ["index: --quick not in --help"]


def test_a_command_without_a_section_is_drift() -> None:
    skill = run_cli(["skill"]).stdout
    edited = skill.replace("## `lorekeep restore`", "## Restoring")

    assert drift(edited) == ["restore: no section in SKILL.md"]


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
