"""The Store: one flat folder of immutable Versions, written through one commit point.

Everything that writes to a Store goes through `commit`, which takes the one lock, renames the
Version and its Original into place, appends the CSV rows that are not already there and notifies
the Index. `lock` is the only place the lock file (`LOCK_FILE`) is opened; the commit, an Index
rebuild and the package regeneration share it and none of them nests it (`flock` is not re-entrant).
A Tag row and an alias row are appended once; a Recheck row and a withdrawal row are appended
every time.
"""

from __future__ import annotations

import contextlib
import csv
import fcntl
import os
import re
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import astuple, dataclass, fields
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from lorekeep import frontmatter, history
from lorekeep.project import HostRule
from lorekeep.urls import normalise, under

LOCK_FILE = ".lorekeep.lock"
TAGS_FILE = "tags.csv"
CHECKS_FILE = "checks.csv"
ALIASES_FILE = "aliases.csv"
CITATIONS_FILE = "citations.csv"
WITHDRAWALS_FILE = "withdrawals.csv"
INDEX_FILE = "sources.db"
MAX_NAME_BYTES = 200
OWNER_SCHEME = "owner:"
"""The scheme of an owner's Source (`owner:<slug>`): it has no publisher to ask."""


class LockError(RuntimeError):
    """The Store lock was taken while this process already held it; that would deadlock."""


_held: set[Path] = set()


@contextlib.contextmanager
def lock(store: Path) -> Iterator[None]:
    """Hold the Store's lock file exclusively (`flock`); never nested inside itself."""
    store = store.resolve()
    if store in _held:
        raise LockError(f"the Store lock on {store} is already held by this command")
    fd = os.open(store / LOCK_FILE, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        _held.add(store)
        try:
            yield
        finally:
            _held.discard(store)
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class TagRow:
    url: str
    tag: str
    added_at: str


RECHECK_RESULTS = ("unchanged", "changed", "gone", "error")
type RecheckResult = Literal["unchanged", "changed", "gone", "error"]


@dataclass(frozen=True)
class RecheckRow:
    url: str
    checked_at: str
    result: str
    status: str
    sha256: str


@dataclass(frozen=True)
class AliasRow:
    alias: str
    url: str
    added_at: str


WITHDRAW, UNDO = "withdraw", "undo"
WITHDRAWAL_ACTIONS = (WITHDRAW, UNDO)


@dataclass(frozen=True)
class WithdrawalRow:
    """One Curator's act on a Source (ADR 0010): `withdraw` takes it out of every Run's view,
    `undo` brings it back; the last row of a `url` says which holds."""

    url: str
    recorded_at: str
    action: str
    reason: str


type Row = TagRow | RecheckRow | AliasRow | WithdrawalRow

FILE_OF: Mapping[type[Row], str] = {
    TagRow: TAGS_FILE,
    RecheckRow: CHECKS_FILE,
    AliasRow: ALIASES_FILE,
    WithdrawalRow: WITHDRAWALS_FILE,
}
"""The CSV each row type lives in; a row's fields, in order, are that file's columns."""

WATCHED_FILES = (*FILE_OF.values(), CITATIONS_FILE)
"""The files that grow: the Index fingerprints them, the backup copies them every time."""


def columns(row_type: type[Row]) -> tuple[str, ...]:
    return tuple(field.name for field in fields(row_type))


def table_of(row_type: type[Row]) -> str:
    """The Index table that mirrors the row type's file (`tags.csv` → `tags`)."""
    return FILE_OF[row_type].removesuffix(".csv")


def row_key(row: Row) -> tuple[str, ...] | None:
    """What makes a row 'already present', as its leading columns: a Tag by Source and Tag, an
    alias by its pair. A Recheck has no key: every Recheck is appended whatever its answer, two
    in one second too; nor has a withdrawal, which `withdraw` appends only when it changes what
    holds."""
    if isinstance(row, TagRow):
        return (row.url, row.tag)
    if isinstance(row, AliasRow):
        return (row.alias, row.url)
    return None


@dataclass(frozen=True)
class NewVersion:
    """A Version to store: its Provenance, its Markdown body and, when kept, its Original."""

    frontmatter: frontmatter.Fields
    body: bytes
    original: bytes | None = None
    original_ext: str | None = None


@dataclass(frozen=True)
class VersionInfo:
    """A stored Version as the lookup reports it."""

    path: Path
    frontmatter: dict[str, Any]

    @classmethod
    def read(cls, path: Path) -> VersionInfo:
        """The Version at `path`, from the head of its file."""
        return cls(path, read_head(path))

    @property
    def url(self) -> str:
        return str(self.frontmatter["url"])

    @property
    def sha256(self) -> str:
        return str(self.frontmatter["sha256"])

    @property
    def fetched_at(self) -> str:
        return str(self.frontmatter["fetched_at"])


def version_name(url: str, sha256: str) -> str:
    """`<host>--<path, every / and unsafe character as ->--<sha8>.md`, under 200 bytes.

    The path part is cut when the name would be longer; the hash keeps it unique and the full
    `url` is in the frontmatter. An owner's Source (`owner:<slug>`) is `owner--<slug>--<sha8>.md`.
    """
    if url.startswith(OWNER_SCHEME):
        host, rest = "owner", url[len(OWNER_SCHEME) :]
    else:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        rest = parts.path + (f"?{parts.query}" if parts.query else "")
    path_part = re.sub(r"-{2,}", "-", re.sub(r"[^A-Za-z0-9._]", "-", rest)).strip("-.")
    tail = f"--{sha256[:8]}.md"
    room = MAX_NAME_BYTES - len(f"{host}--{tail}".encode()) - 1
    while len(path_part.encode()) > room:
        path_part = path_part[:-1]
    return f"{host}--{path_part.rstrip('-.')}{tail}"


def stem(name: str) -> str:
    """The Version's file name without `.md`, hash included; its Original is `<stem>.orig.<ext>`."""
    return name.removesuffix(".md")


def commit(
    store: Path,
    version: NewVersion | None = None,
    tags: Sequence[TagRow] = (),
    checks: Sequence[RecheckRow] = (),
    aliases: Sequence[AliasRow] = (),
    withdrawals: Sequence[WithdrawalRow] = (),
) -> Path | None:
    """The one commit point: write what is new, append what is not there yet, notify the Index.

    Returns the Version's path (new or already present) when a Version was given. Every writer
    passes what it has — a Version, Tag rows, Recheck rows, alias rows, withdrawal rows, any of
    them empty.
    """
    with lock(store):
        path: Path | None = None
        if version is not None:
            url = str(version.frontmatter["url"])
            sha256 = str(version.frontmatter["sha256"])
            path = store / version_name(url, sha256)
            _write_once(path, frontmatter.render(version.frontmatter) + version.body)
            if version.original is not None:
                ext = (version.original_ext or "bin").lstrip(".")
                _write_once(store / f"{stem(path.name)}.orig.{ext}", version.original)
        _append_missing(store, TagRow, tags)
        _append_missing(store, RecheckRow, checks)
        _append_missing(store, AliasRow, aliases)
        _append_missing(store, WithdrawalRow, withdrawals)
        from lorekeep import index  # the Index derives from the Store, so it imports this module

        index.notify(
            store,
            version=path,
            tags=tags,
            checks=checks,
            aliases=aliases,
            withdrawals=withdrawals,
        )
        return path


def _write_once(target: Path, data: bytes) -> None:
    """Write `data` to `<name>.tmp-<pid>` and rename it into place; an existing target is left
    alone (same name means same hash and same bytes)."""
    if target.exists():
        return
    tmp = target.with_name(f"{target.name}.tmp-{os.getpid()}")
    with open(tmp, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, target)


def read_rows[R: Row](store: Path, row_type: type[R]) -> list[R]:
    """Every row of the CSV that keeps `row_type` (`tags.csv`, `checks.csv`, `aliases.csv`,
    `withdrawals.csv`)."""
    path = store / FILE_OF[row_type]
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [row_type(**{column: row[column] for column in columns(row_type)}) for row in reader]


def _append_missing(store: Path, row_type: type[Row], rows: Sequence[Row]) -> None:
    """Append the rows whose key is not in the file yet; a row without a key is always new."""
    if not rows:
        return
    present = {row_key(row) for row in read_rows(store, row_type)}
    new = [row for row in rows if row_key(row) is None or row_key(row) not in present]
    if not new:
        return
    path = store / FILE_OF[row_type]
    header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        if header:
            writer.writerow(columns(row_type))
        writer.writerows(astuple(row) for row in new)
        handle.flush()
        os.fsync(handle.fileno())


def latest(store: Path, url: str, rules: Sequence[HostRule]) -> VersionInfo | None:
    """The latest Version of `url` (normalised, Twin-reduced, or an alias of a stored `url`).

    A current Index answers in one query without a lock; otherwise every `.md` frontmatter is
    read and the Latest Version rule (`history.latest`) picks among them. A lookup never
    rebuilds the Index.
    """
    wanted = normalise(url, rules)
    aliases = {row.alias: row.url for row in read_rows(store, AliasRow)}
    wanted = aliases.get(wanted, wanted)
    from lorekeep import index

    with index.current(store) as reader:
        if reader is not None:
            return reader.latest(wanted)
    versions = [info for info in scan(store) if info.url == wanted]
    checks = [row for row in read_rows(store, RecheckRow) if row.url == wanted]
    sha256 = history.latest(
        [(info.fetched_at, info.sha256) for info in versions],
        [(row.checked_at, row.sha256) for row in checks],
    )
    return next((info for info in versions if info.sha256 == sha256), None)


def withdrawn(store: Path) -> dict[str, WithdrawalRow]:
    """The Sources withdrawn now, by `url`, each with the row that withdrew it: those whose last
    `withdrawals.csv` row is a `withdraw`. The file is read directly, so the answer never waits
    for the Index."""
    last: dict[str, WithdrawalRow] = {}
    for row in read_rows(store, WithdrawalRow):
        last[row.url] = row
    return {url: row for url, row in last.items() if row.action == WITHDRAW}


def source_urls(store: Path, prefix: str) -> list[str]:
    """Every Source's `url` `under` `prefix`, sorted: from a current Index without a
    lock, else from every `.md` frontmatter. Never rebuilds the Index."""
    from lorekeep import index

    with index.current(store) as reader:
        if reader is not None:
            return reader.urls(prefix)
    return sorted({info.url for info in scan(store) if under(info.url, prefix)})


def scan(store: Path) -> Iterator[VersionInfo]:
    """Every Version in the Store, from the head of each `.md` file; a `.md` file that is not
    a Version is left out (`not_a_version`)."""
    for path in sorted(store.glob("*.md")):
        try:
            yield VersionInfo.read(path)
        except frontmatter.FrontmatterError as error:
            not_a_version(path, error)


REQUIRED_FIELDS = ("url", "sha256", "fetched_at")
"""What makes a `.md` file's frontmatter a Version's: without them it is someone's note."""

_ignored: set[Path] = set()


def not_a_version(path: Path, error: frontmatter.FrontmatterError) -> None:
    """Say on stderr, once per command run (`forget_ignored`), that the `.md` file at `path`
    is not a Version and is ignored: an owner's note or the source file of an `add` may sit in
    the Store's folder, and no reader or rebuild fails because of it."""
    if path in _ignored:
        return
    _ignored.add(path)
    print(f"lorekeep: warning: {path.name}: not a Version ({error}), ignored", file=sys.stderr)


def forget_ignored() -> None:
    """Start a command run: every `.md` file that is not a Version is named again."""
    _ignored.clear()


def parse_version(data: bytes) -> tuple[dict[str, Any], bytes]:
    """A Version file's frontmatter and body; `FrontmatterError` when it is not a Version's."""
    fields, body = frontmatter.parse(data)
    for name in REQUIRED_FIELDS:
        if name not in fields:
            raise frontmatter.FrontmatterError(f"no {name} in the frontmatter")
    return fields, body


def read_head(path: Path) -> dict[str, Any]:
    """A Version's frontmatter, reading only up to its closing fence."""
    head = bytearray()
    with path.open("rb") as handle:
        first = handle.readline()
        if first != frontmatter.FENCE:
            raise frontmatter.FrontmatterError("no frontmatter")
        head += first
        for line in handle:
            head += line
            if line == frontmatter.FENCE:
                break
    fields, _ = parse_version(bytes(head))
    return fields
