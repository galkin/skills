"""`backup`, `restore` and the data package, through the command layer with a fake runner."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from frictionless import validate

from lorekeep.edges import Edges
from tests.support import FIXTURES, FakeFetcher, FakeRunner, FakeTransport, run_cli, write_version

BUCKET = "test-sources"
TWIN = FIXTURES / "anthropic-prompt-caching.twin"
AWS = FIXTURES / "aws-prompt-caching.twin"


def make_store(tmp_path: Path, *, bucket: str | None = BUCKET) -> Path:
    """A Store with two web Versions, an owner's Version, `tags.csv` and no `citations.csv`."""
    store = tmp_path / "store"
    store.mkdir()
    if bucket is not None:
        (store / "lorekeep.toml").write_text(f'bucket = "{bucket}"\n', encoding="utf-8")
    write_version(
        store,
        TWIN,
        fetched_at="2026-10-01T08:00:00Z",
        url="https://platform.claude.com/docs/en/build-with-claude/prompt-caching",
        publisher="anthropic",
        authority="primary",
        converter="md-twin",
    )
    write_version(store, AWS, fetched_at="2026-10-02T09:30:00Z")
    note = tmp_path / "note.md"
    note.write_text("# Research\n\nPasted from a chat.\n", encoding="utf-8")
    added = run_cli(
        ["add", str(note), "--title", "Research", "--tag", "anthropic", "--store", str(store)]
    )
    assert added.exit_code == 0, added.stderr
    return store


def edges(runner: FakeRunner) -> Edges:
    return Edges(transport=FakeTransport([]), fetcher=FakeFetcher(), runner=runner)


def package(store: Path) -> dict[str, Any]:
    return json.loads((store / "datapackage.json").read_text(encoding="utf-8"))


def resource(store: Path, name: str) -> dict[str, Any]:
    (found,) = [r for r in package(store)["resources"] if r["name"] == name]
    return found


def test_backup_writes_a_valid_data_package_with_one_sources_row_per_version(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)

    result = run_cli(["backup", "--store", str(store)], edges=edges(FakeRunner()))

    assert result.exit_code == 0, result.stderr
    report = validate(str(store / "datapackage.json"))
    assert report.valid, report.flatten(["taskNumber", "rowNumber", "fieldName", "type", "note"])
    names = {r["name"] for r in package(store)["resources"]}
    assert names == {"tags", "sources"}
    rows = resource(store, "sources")["data"]
    versions = sorted(path.name for path in store.glob("*.md"))
    assert sorted(row["file"] for row in rows) == versions
    assert len(rows) == 3
    twin = next(row for row in rows if row["publisher"] == "anthropic")
    digest = hashlib.sha256((TWIN / "body.md").read_bytes()).hexdigest()
    assert twin == {
        "url": "https://platform.claude.com/docs/en/build-with-claude/prompt-caching",
        "file": f"platform.claude.com--docs-en-build-with-claude-prompt-caching--{digest[:8]}.md",
        "sha256": digest,
        "bytes": (store / twin["file"]).stat().st_size,
        "fetched_at": "2026-10-01T08:00:00Z",
        "publisher": "anthropic",
        "authority": "primary",
        "converter": "md-twin",
    }


EXCLUDED = [
    "tags.csv",
    "checks.csv",
    "aliases.csv",
    "citations.csv",
    "datapackage.json",
    "lorekeep.toml",
    "sources.db",
    "sources.db-wal",
    "sources.db-shm",
    ".lorekeep.lock",
    "x.md.tmp-123",
]

KEPT = [
    "platform.claude.com--docs-en-build-with-claude-prompt-caching--1a2b3c4d.md",
    "platform.claude.com--docs-en-build-with-claude-prompt-caching--1a2b3c4d.orig.html",
    "example.com--reports-tags.csv--0f0f0f0f.md",
    "example.com--sources.db--0f0f0f0f.orig.bin",
    "owner--research--9e8d7c6b.md",
]


def exclude_pattern(argv: list[str]) -> re.Pattern[str]:
    (value,) = [arg.removeprefix("--exclude=") for arg in argv if arg.startswith("--exclude=")]
    return re.compile(value)


def test_backup_runs_one_no_clobber_rsync_and_one_cp_of_the_growing_files(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    runner = FakeRunner()

    result = run_cli(["backup", "--store", str(store)], edges=edges(runner))

    assert result.exit_code == 0, result.stderr
    assert len(runner.calls) == 2
    rsync, cp = runner.calls
    assert rsync[:3] == ["gcloud", "storage", "rsync"]
    assert "--recursive" in rsync
    assert "--no-clobber" in rsync
    assert not any(arg.startswith("--delete") for arg in rsync)
    assert "--dry-run" not in rsync
    assert rsync[-2:] == [str(store), f"gs://{BUCKET}"]
    pattern = exclude_pattern(rsync)
    for name in EXCLUDED:
        assert pattern.search(name), name
    for name in KEPT + sorted(path.name for path in store.iterdir() if path.suffix == ".md"):
        assert not pattern.search(name), name
    assert cp[:3] == ["gcloud", "storage", "cp"]
    assert cp[-1] == f"gs://{BUCKET}/"
    assert cp[3:-1] == [
        str(store / "tags.csv"),
        str(store / "datapackage.json"),
        str(store / "lorekeep.toml"),
    ]


def test_dry_run_passes_the_flag_to_rsync_runs_no_cp_and_prints_what_cp_would_copy(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    runner = FakeRunner([(0, "Would copy file://x.md to gs://test-sources/x.md\n", "")])

    result = run_cli(["backup", "--dry-run", "--store", str(store)], edges=edges(runner))

    assert result.exit_code == 0, result.stderr
    (rsync,) = runner.calls
    assert rsync[:3] == ["gcloud", "storage", "rsync"]
    assert "--dry-run" in rsync
    assert "Would copy file://x.md" in result.stdout
    for name in ("tags.csv", "datapackage.json", "lorekeep.toml"):
        assert str(store / name) in result.stdout
    for name in ("checks.csv", "aliases.csv", "citations.csv"):
        assert name not in result.stdout
    assert validate(str(store / "datapackage.json")).valid
    assert len(resource(store, "sources")["data"]) == 3


def test_the_package_types_the_status_of_checks_csv_as_a_string(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    url = "https://platform.claude.com/docs/en/build-with-claude/prompt-caching"
    (store / "checks.csv").write_text(
        "url,checked_at,result,status,sha256\n"
        f"{url},2026-10-03T10:00:00Z,unchanged,304,{'ab' * 32}\n"
        f"{url},2026-10-04T10:00:00Z,error,ReadTimeout,{'ab' * 32}\n",
        encoding="utf-8",
    )

    result = run_cli(["backup", "--store", str(store)], edges=edges(FakeRunner()))

    assert result.exit_code == 0, result.stderr
    report = validate(str(store / "datapackage.json"))
    assert report.valid, report.flatten(["taskNumber", "rowNumber", "fieldName", "type", "note"])
    fields = {f["name"]: f for f in resource(store, "checks")["schema"]["fields"]}
    assert list(fields) == ["url", "checked_at", "result", "status", "sha256"]
    assert fields["status"]["type"] == "string"


def test_backup_without_a_bucket_exits_non_zero_with_a_message(tmp_path: Path) -> None:
    store = make_store(tmp_path, bucket=None)
    runner = FakeRunner()

    result = run_cli(["backup", "--store", str(store)], edges=edges(runner))

    assert result.exit_code != 0
    assert "bucket" in result.stderr
    assert runner.calls == []


def test_restore_copies_one_object_from_the_bucket_into_the_store(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    runner = FakeRunner()
    name = "example.com--gone-page--0f0f0f0f.md"

    result = run_cli(["restore", name, "--store", str(store)], edges=edges(runner))

    assert result.exit_code == 0, result.stderr
    assert runner.calls == [["gcloud", "storage", "cp", f"gs://{BUCKET}/{name}", f"{store}/"]]


def test_restore_of_a_generation_names_it_with_a_hash_suffix(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    runner = FakeRunner()

    result = run_cli(
        ["restore", "checks.csv", "--generation", "1760700000123456", "--store", str(store)],
        edges=edges(runner),
    )

    assert result.exit_code == 0, result.stderr
    assert runner.calls == [
        ["gcloud", "storage", "cp", f"gs://{BUCKET}/checks.csv#1760700000123456", f"{store}/"]
    ]


def test_restore_refuses_to_overwrite_a_local_file_and_runs_nothing(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    runner = FakeRunner()
    before = (store / "tags.csv").read_bytes()

    result = run_cli(["restore", "tags.csv", "--store", str(store)], edges=edges(runner))

    assert result.exit_code != 0
    assert "tags.csv" in result.stderr
    assert "exists" in result.stderr
    assert runner.calls == []
    assert (store / "tags.csv").read_bytes() == before


HOLD_LOCK = """
import fcntl, sys, time
handle = open(sys.argv[1], "a")
fcntl.flock(handle, fcntl.LOCK_EX)
print("held", flush=True)
time.sleep(float(sys.argv[2]))
"""


def test_backup_regenerates_the_package_under_the_store_lock(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    holder = subprocess.Popen(
        [sys.executable, "-c", HOLD_LOCK, str(store / ".lorekeep.lock"), "0.6"],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None
        assert holder.stdout.readline().strip() == "held"
        started = time.monotonic()

        result = run_cli(["backup", "--store", str(store)], edges=edges(FakeRunner()))

        waited = time.monotonic() - started
    finally:
        holder.wait(timeout=10)
    assert result.exit_code == 0, result.stderr
    assert waited >= 0.4
    assert (store / "datapackage.json").is_file()


def test_a_failed_rsync_stops_the_backup_before_the_cp(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    runner = FakeRunner([(1, "", "ERROR: (gcloud.storage.rsync) 403 Forbidden\n")])

    result = run_cli(["backup", "--store", str(store)], edges=edges(runner))

    assert result.exit_code != 0
    assert "403 Forbidden" in result.stderr
    assert len(runner.calls) == 1


def test_the_package_describes_citations_csv_with_or_without_as_of(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    url = "https://platform.claude.com/docs/en/build-with-claude/prompt-caching"
    (store / "citations.csv").write_text(
        f"work_id,url,as_of\nlesson-1,{url},2026-09-01\nlesson-2,{url},2026-09-02T10:00:00Z\n",
        encoding="utf-8",
    )

    run_cli(["backup", "--store", str(store)], edges=edges(FakeRunner()))

    report = validate(str(store / "datapackage.json"))
    assert report.valid, report.flatten(["taskNumber", "rowNumber", "fieldName", "type", "note"])
    fields = [f["name"] for f in resource(store, "citations")["schema"]["fields"]]
    assert fields == ["work_id", "url", "as_of"]

    (store / "citations.csv").write_text(f"work_id,url\nlesson-1,{url}\n", encoding="utf-8")

    run_cli(["backup", "--store", str(store)], edges=edges(FakeRunner()))

    assert validate(str(store / "datapackage.json")).valid
    fields = [f["name"] for f in resource(store, "citations")["schema"]["fields"]]
    assert fields == ["work_id", "url"]


def test_restore_takes_a_bare_name_in_the_store_and_needs_a_bucket(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    runner = FakeRunner()

    nested = run_cli(["restore", "../elsewhere.md", "--store", str(store)], edges=edges(runner))
    generation = run_cli(
        ["restore", "x.md", "--generation", "latest", "--store", str(store)], edges=edges(runner)
    )
    (store / "lorekeep.toml").unlink()
    unbucketed = run_cli(["restore", "x.md", "--store", str(store)], edges=edges(runner))

    assert nested.exit_code != 0
    assert generation.exit_code != 0
    assert unbucketed.exit_code != 0
    assert "bucket" in unbucketed.stderr
    assert runner.calls == []
