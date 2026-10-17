from pathlib import Path

from tests.support import run_cli

SUBCOMMANDS = [
    "get",
    "add",
    "search",
    "index",
    "recheck",
    "backup",
    "restore",
    "tag",
    "status",
    "skill",
]


def test_help_lists_every_subcommand() -> None:
    result = run_cli(["--help"])

    assert result.exit_code == 0
    for name in SUBCOMMANDS:
        assert name in result.stdout


def test_status_on_a_new_store_counts_zero_versions(tmp_path: Path) -> None:
    result = run_cli(["status"], env={"LOREKEEP_STORE": str(tmp_path)})

    assert result.exit_code == 0
    assert "0 Versions" in result.stdout


def test_store_flag_on_status_names_the_store(tmp_path: Path) -> None:
    result = run_cli(["status", "--store", str(tmp_path)])

    assert result.exit_code == 0
    assert "0 Versions" in result.stdout


def test_a_missing_store_setting_is_a_one_line_error() -> None:
    result = run_cli(["status"])

    assert result.exit_code != 0
    assert "LOREKEEP_STORE" in result.stderr
    assert len(result.stderr.strip().splitlines()) == 1


def test_a_store_that_does_not_exist_is_an_error_and_is_not_created(tmp_path: Path) -> None:
    missing = tmp_path / "nowhere" / "store"

    result = run_cli(["status", "--store", str(missing)])

    assert result.exit_code != 0
    assert str(missing) in result.stderr
    assert len(result.stderr.strip().splitlines()) == 1
    assert not (tmp_path / "nowhere").exists()


def test_a_store_flag_overrides_the_environment(tmp_path: Path) -> None:
    result = run_cli(
        ["status", "--store", str(tmp_path)], env={"LOREKEEP_STORE": str(tmp_path / "gone")}
    )

    assert result.exit_code == 0


def test_get_and_add_without_a_tag_are_one_line_errors(tmp_path: Path) -> None:
    env = {"LOREKEEP_STORE": str(tmp_path)}
    note = tmp_path.parent / "note.md"
    note.write_text("# Research\n")

    for argv in (["get", "https://example.test/page"], ["add", str(note), "--title", "Research"]):
        result = run_cli(argv, env=env)

        assert result.exit_code != 0, argv
        assert "LOREKEEP_TAG" in result.stderr, argv
        assert len(result.stderr.strip().splitlines()) == 1, argv
    assert list(tmp_path.iterdir()) == []


def test_only_get_and_add_need_a_tag(tmp_path: Path) -> None:
    env = {"LOREKEEP_STORE": str(tmp_path)}

    assert run_cli(["status"], env=env).exit_code == 0
    for argv in (["search", "caching"], ["recheck"], ["index"], ["backup"]):
        assert "LOREKEEP_TAG" not in run_cli(argv, env=env).stderr, argv


def test_the_root_parser_takes_no_flag_but_help(tmp_path: Path) -> None:
    root_help = run_cli(["--help"]).stdout
    options = root_help.split("options:")[1]

    assert [line.split()[0] for line in options.strip().splitlines()] == ["-h,"]
    for argv in (["--store", str(tmp_path), "status"], ["--tag", "aws", "status"]):
        assert run_cli(argv).exit_code == 2, argv


def test_tag_is_single_on_get_and_add(tmp_path: Path) -> None:
    env = {"LOREKEEP_STORE": str(tmp_path)}
    note = tmp_path.parent / "note.md"
    note.write_text("# Research\n")

    for argv in (
        ["get", "https://example.test/page", "--tag", "aws", "--tag", "nvidia"],
        ["add", str(note), "--title", "Research", "--tag", "aws", "--tag", "nvidia"],
    ):
        result = run_cli(argv, env=env)

        assert result.exit_code == 2, argv
        assert "--tag may be given once" in result.stderr, argv
    assert list(tmp_path.iterdir()) == []


def test_tag_is_repeatable_on_search_and_recheck(tmp_path: Path) -> None:
    env = {"LOREKEEP_STORE": str(tmp_path)}

    for argv in (["search", "caching"], ["recheck"]):
        assert "repeatable" in run_cli([argv[0], "--help"]).stdout
        result = run_cli([*argv, "--tag", "aws", "--tag", "nvidia"], env=env)
        assert "may be given once" not in result.stderr
        assert "usage:" not in result.stderr


def test_every_subcommand_declares_its_own_flags() -> None:
    expected = {
        "get": ["--tag", "--max-age", "--fresh", "--json", "--store"],
        "add": ["--title", "--publisher", "--authority", "--fetched-at", "--tag", "--json"],
        "search": ["--tag", "--all", "--publisher", "--authority", "--exact", "--limit", "--json"],
        "index": ["--store"],
        "recheck": ["--tag", "--publisher", "--prefix", "--citations", "--dry-run", "--store"],
        "backup": ["--dry-run", "--store"],
        "restore": ["--generation", "--store"],
        "status": ["--json", "--store"],
        "skill": ["--install", "--force"],
    }
    for command, flags in expected.items():
        help_text = run_cli([command, "--help"]).stdout
        for flag in flags:
            assert flag in help_text, (command, flag)
    tag_add = run_cli(["tag", "add", "--help"]).stdout
    assert "--prefix" in tag_add
    assert "--store" in tag_add
