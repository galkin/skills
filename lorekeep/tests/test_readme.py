"""The README is the owner's manual: it must keep naming what the owner needs to run lorekeep."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent
README = (ROOT / "README.md").read_text()


def test_the_readme_covers_install_settings_and_recovery() -> None:
    for needed in (
        "uv tool install",
        "[browser]",
        "LOREKEEP_STORE",
        "LOREKEEP_TAG",
        "lorekeep.toml",
        "src/lorekeep/hosts.toml",
        "~/orca/sources/agentic-system.design/",
        "agentic-system-design-sources",
        "lorekeep restore ",
        "--generation",
        "gcloud storage rsync --recursive gs://",
        "lorekeep index",
        "scripts/smoke.py",
        "per-call override",
        "ADR 0008",
    ):
        assert needed in README, needed


def test_the_readmes_host_table_lists_every_default_rule() -> None:
    defaults = tomllib.loads((ROOT / "src" / "lorekeep" / "hosts.toml").read_text())

    for rule in defaults["hosts"]:
        assert f"| `{rule['prefix']}`" in README, rule["prefix"]
        assert f"`{rule['publisher']}`" in README, rule["publisher"]
