"""The Index: `sources.db`, derived from the Store's files.

It holds every Version's Provenance, the rows of `tags.csv`, `checks.csv` and `aliases.csv`, and
the Versions' Sections with an FTS5 table over them. It is rebuilt in place, in one transaction,
under the Store lock (`rebuild`, `ensure`); every commit notifies it (`notify`), so it stays
current between rebuilds. It answers through one `Reader`: `current` opens one over a current
Index without any lock and never rebuilds (`None` when the Index is missing, stale or
unreadable, and the caller reads the files); `ensured` brings the Index up to date first.
"""

from __future__ import annotations

import contextlib
import csv
import sqlite3
import sys
from collections.abc import Iterator, Sequence
from dataclasses import astuple, dataclass
from datetime import UTC, datetime
from pathlib import Path

from lorekeep import history, sections
from lorekeep import store as store_module
from lorekeep.frontmatter import FrontmatterError
from lorekeep.project import HostRule
from lorekeep.provenance import TIME_FORMAT
from lorekeep.store import (
    CITATIONS_FILE,
    FILE_OF,
    INDEX_FILE,
    WATCHED_FILES,
    AliasRow,
    RecheckRow,
    Row,
    TagRow,
    VersionInfo,
)
from lorekeep.urls import normalise, unknown_host

_VERSION_COLUMNS = (
    "url",
    "fetched_at",
    "sha256",
    "publisher",
    "authority",
    "converter",
    "etag",
    "last_modified",
    "title",
    "modified",
    "canonical",
    "origin",
)
_ORIGINAL_COLUMNS = ("url", "mediatype", "sha256", "stored")
SCHEMA_VERSION = "3"
"""Bumped whenever a table's columns change, so an Index built by an older lorekeep reads as stale
and is rebuilt with the new tables (2: `versions.canonical`; 3: `sections.heading_line` beside
`sections.line`, which is now the Section's first text line)."""

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS versions(
  file TEXT PRIMARY KEY,
  {", ".join(f"{column} TEXT" for column in _VERSION_COLUMNS)},
  {", ".join(f"original_{column} TEXT" for column in _ORIGINAL_COLUMNS)}
);
CREATE INDEX IF NOT EXISTS versions_url ON versions(url);
CREATE TABLE IF NOT EXISTS tags(url TEXT, tag TEXT, added_at TEXT);
CREATE INDEX IF NOT EXISTS tags_url ON tags(url);
CREATE TABLE IF NOT EXISTS checks(url TEXT, checked_at TEXT, result TEXT, status TEXT, sha256 TEXT);
CREATE INDEX IF NOT EXISTS checks_url ON checks(url);
CREATE TABLE IF NOT EXISTS aliases(alias TEXT, url TEXT, added_at TEXT);
CREATE TABLE IF NOT EXISTS citations(work_id TEXT, url TEXT, as_of TEXT);
CREATE TABLE IF NOT EXISTS sections(
  id INTEGER PRIMARY KEY,
  file TEXT NOT NULL,
  heading TEXT NOT NULL,
  heading_line INTEGER,
  line INTEGER NOT NULL,
  body TEXT NOT NULL,
  ord INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS sections_file ON sections(file);
CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts USING fts5(
  heading, body, content='sections', content_rowid='id', tokenize='porter unicode61'
);
-- The Latest Version of each Source, as `history.latest` says it and a test proves: the one its
-- latest `checks.csv` row names, else the newest `fetched_at`; a tie on `checked_at` goes to the
-- later row in the file (rows enter `checks` in file order, so `rowid` is that order).
DROP VIEW IF EXISTS latest;
CREATE VIEW latest AS
SELECT v.* FROM versions v
WHERE v.file = (
  SELECT w.file FROM versions w
  WHERE w.url = v.url
  ORDER BY w.sha256 = (
    SELECT c.sha256 FROM checks c
    WHERE c.url = v.url AND c.sha256 != ''
    ORDER BY c.checked_at DESC, c.rowid DESC LIMIT 1
  ) DESC, w.fetched_at DESC, w.file
  LIMIT 1
);
"""


def _connect(store: Path) -> sqlite3.Connection:
    """The one connection to the Store's Index: WAL mode, a busy timeout, explicit transactions.
    It creates the file when there is none, so a reader checks `_exists` first."""
    con = sqlite3.connect(store / INDEX_FILE, timeout=30.0, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def _exists(store: Path) -> bool:
    return (store / INDEX_FILE).is_file()


@dataclass(frozen=True)
class Counts:
    """What a rebuild put into the Index, and what it had to leave out (one warning per
    malformed `citations.csv` row, with its line number)."""

    versions: int
    sections: int
    tags: int
    checks: int
    aliases: int
    citations: int = 0
    warnings: tuple[str, ...] = ()


def rebuild(store: Path, rules: Sequence[HostRule]) -> Counts:
    """Empty and refill every table from the Store's files, in place, under the Store lock;
    `rules` normalise the addresses `citations.csv` names."""
    with store_module.lock(store):
        return _rebuild_locked(store, rules)


def ensure(store: Path, rules: Sequence[HostRule]) -> Counts | None:
    """Bring the Index up to date before a reader queries it: compare `meta` with the files
    without any lock; only when the file is missing or stale take the Store lock, compare again
    and rebuild in place. Returns the rebuild's counts, or `None` when the Index was current, so
    six readers finding none produce one build and a query on a current Index never waits."""
    if _looks_current(store):
        return None
    with store_module.lock(store):
        if _looks_current(store):
            return None
        return _rebuild_locked(store, rules)


def report(counts: Counts | None, *, note: bool = True) -> None:
    """Print a rebuild's warnings to stderr, and, unless `note` is off, one line saying the
    Index was rebuilt — so a log of six readers shows how many rebuilt it; nothing when there
    was no rebuild."""
    if counts is None:
        return
    if note:
        print(
            f"lorekeep: note: the Index was missing or stale and was rebuilt "
            f"({counts.versions} Versions, {counts.sections} Sections)",
            file=sys.stderr,
        )
    for warning in counts.warnings:
        print(warning, file=sys.stderr)


def _looks_current(store: Path) -> bool:
    with current(store) as reader:
        return reader is not None


def _rebuild_locked(store: Path, rules: Sequence[HostRule]) -> Counts:
    con = _connect(store)
    try:
        if _schema_of(con) != SCHEMA_VERSION:
            # `CREATE TABLE IF NOT EXISTS` keeps an older table's columns; every table but
            # `meta` is rebuilt from the files anyway.
            con.executescript(_DROP)
        con.executescript(_SCHEMA)
        con.execute("BEGIN IMMEDIATE")
        try:
            tables = ("versions", "tags", "checks", "aliases", "citations", "sections", "meta")
            for table in tables:
                con.execute(f"DELETE FROM {table}")
            con.execute("INSERT INTO sections_fts(sections_fts) VALUES('delete-all')")
            versions = sections = ignored = 0
            for path in sorted(store.glob("*.md")):
                try:
                    sections += _index_version(con, path)
                except FrontmatterError as error:
                    store_module.not_a_version(path, error)
                    ignored += 1
                    continue
                versions += 1
            tags = _insert_rows(con, TagRow, store_module.read_rows(store, TagRow))
            checks = _insert_rows(con, RecheckRow, store_module.read_rows(store, RecheckRow))
            aliases = _insert_rows(con, AliasRow, store_module.read_rows(store, AliasRow))
            cited, warnings = _read_citations(store, rules)
            con.executemany("INSERT INTO citations VALUES(?, ?, ?)", cited)
            _write_meta(con, store, ignored)
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    finally:
        con.close()
    return Counts(versions, sections, tags, checks, aliases, len(cited), tuple(warnings))


def _read_citations(
    store: Path, rules: Sequence[HostRule]
) -> tuple[list[tuple[str, str, str | None]], list[str]]:
    """The rows of `citations.csv` (`work_id, url[, as_of]`), written by the consuming Project:
    `url` normalised, Twin-reduced and taken through `aliases.csv` like a request, so a work may
    cite the address it was given; `as_of` an ISO 8601 date or timestamp
    brought to UTC `YYYY-MM-DDTHH:MM:SSZ` (a bare date means the end of that day, so a work
    written that day is measured against the Version current then) or `None` when absent. A
    row that cannot be read is left out and named with its line number in the warnings."""
    path = store / CITATIONS_FILE
    if not path.is_file():
        return [], []
    aliases = {row.alias: row.url for row in store_module.read_rows(store, AliasRow)}
    rows: list[tuple[str, str, str | None]] = []
    warnings: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header is None:
            return [], []
        if [column.strip() for column in header[:2]] != ["work_id", "url"]:
            return [], [
                f"lorekeep: warning: {CITATIONS_FILE} line 1: the header is not work_id,url[,as_of]"
            ]
        for row in reader:
            line = reader.line_num
            cells = [cell.strip() for cell in row]
            if not any(cells):
                continue
            if len(cells) < 2 or not cells[0] or not cells[1]:
                warnings.append(
                    f"lorekeep: warning: {CITATIONS_FILE} line {line}: expected work_id,url[,as_of]"
                )
                continue
            as_of = cells[2] if len(cells) > 2 and cells[2] else None
            try:
                when = _as_of(as_of)
            except ValueError:
                warnings.append(
                    f"lorekeep: warning: {CITATIONS_FILE} line {line}: as_of {as_of!r} is not "
                    "an ISO 8601 date or timestamp"
                )
                continue
            url = normalise(cells[1], rules)
            rows.append((cells[0], aliases.get(url, url), when))
    return rows, warnings


def _as_of(text: str | None) -> str | None:
    if text is None:
        return None
    parsed = datetime.fromisoformat(text)
    if len(text) == 10:
        parsed = parsed.replace(hour=23, minute=59, second=59)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).strftime(TIME_FORMAT)


def _index_version(con: sqlite3.Connection, path: Path) -> int:
    """Insert one Version's row and its Sections (with their FTS rows); how many Sections."""
    data = path.read_bytes()
    head, body = store_module.parse_version(data)
    original = head.get("original")
    original = original if isinstance(original, dict) else {}
    values = [path.name]
    values += [_text(head.get(column)) for column in _VERSION_COLUMNS]
    values += [_text(original.get(column)) for column in _ORIGINAL_COLUMNS]
    con.execute(f"INSERT INTO versions VALUES({', '.join('?' * len(values))})", values)
    first_line = data[: len(data) - len(body)].count(b"\n") + 1
    count = 0
    for order, section in enumerate(
        sections.split(body.decode("utf-8", errors="replace"), first_line)
    ):
        cursor = con.execute(
            "INSERT INTO sections(file, heading, heading_line, line, body, ord) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (path.name, section.heading, section.heading_line, section.line, section.body, order),
        )
        con.execute(
            "INSERT INTO sections_fts(rowid, heading, body) VALUES(?, ?, ?)",
            (cursor.lastrowid, section.heading, section.body),
        )
        count += 1
    return count


def _text(value: object) -> str | None:
    return None if value is None else str(value)


def _insert_rows(con: sqlite3.Connection, row_type: type[Row], rows: Sequence[Row]) -> int:
    if rows:
        marks = ", ".join("?" * len(store_module.columns(row_type)))
        table = store_module.table_of(row_type)
        con.executemany(f"INSERT INTO {table} VALUES({marks})", [astuple(row) for row in rows])
    return len(rows)


def _fingerprint(store: Path) -> list[tuple[str, str]]:
    """What the Index records at build time to tell later whether it is current: the count of
    `.md` files and the size and mtime of each watched CSV (`missing` when absent)."""
    values = [("md_files", str(sum(1 for _ in store.glob("*.md"))))]
    for name in WATCHED_FILES:
        path = store / name
        if path.is_file():
            stat = path.stat()
            values += [
                (f"{name}:size", str(stat.st_size)),
                (f"{name}:mtime", str(stat.st_mtime_ns)),
            ]
        else:
            values += [(f"{name}:size", "missing"), (f"{name}:mtime", "missing")]
    return values


_SCHEMA_KEY = "schema"
"""The `meta` key holding the `SCHEMA_VERSION` the Index was built with."""

_DROP = """
DROP VIEW IF EXISTS latest;
DROP TABLE IF EXISTS sections_fts;
DROP TABLE IF EXISTS sections;
DROP TABLE IF EXISTS versions;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS checks;
DROP TABLE IF EXISTS aliases;
DROP TABLE IF EXISTS citations;
"""


def _schema_of(con: sqlite3.Connection) -> str | None:
    try:
        row = con.execute("SELECT value FROM meta WHERE key = ?", (_SCHEMA_KEY,)).fetchone()
    except sqlite3.Error:
        return None
    return str(row[0]) if row else None


_IGNORED = "md_ignored"
"""The `meta` key for how many of the `md_files` are not Versions and have no `versions` row,
so a commit can tell that `versions` still accounts for every `.md` file."""


def _write_meta(con: sqlite3.Connection, store: Path, ignored: int) -> None:
    con.execute("DELETE FROM meta")
    values = [*_fingerprint(store), (_IGNORED, str(ignored)), (_SCHEMA_KEY, SCHEMA_VERSION)]
    con.executemany("INSERT INTO meta(key, value) VALUES(?, ?)", values)


def _is_current(store: Path, con: sqlite3.Connection) -> bool:
    """Whether the Index's `meta` still describes the Store's files; no lock is taken."""
    try:
        recorded = dict(con.execute("SELECT key, value FROM meta").fetchall())
    except sqlite3.Error:
        return False
    recorded.pop(_IGNORED, None)
    if recorded.pop(_SCHEMA_KEY, None) != SCHEMA_VERSION:
        return False
    return bool(recorded) and recorded == dict(_fingerprint(store))


# Notification -----------------------------------------------------------------------------------


def notify(
    store: Path,
    *,
    version: Path | None,
    tags: Sequence[TagRow],
    checks: Sequence[RecheckRow],
    aliases: Sequence[AliasRow],
) -> None:
    """Tell the Index what a commit wrote, in one small transaction, under the Store lock.

    A missing Index is left missing (a commit never builds one). The Version and the rows not
    already in the Index are inserted; then, when every table agrees with the files the commit
    touched and no file it did not touch has changed, `meta` is brought up to date in the same
    transaction, so the commit never looks like staleness. Otherwise `meta` is left as it was and
    the Index stays stale for the next reader to rebuild. An Index built with another
    `SCHEMA_VERSION` is left alone the same way.
    """
    if not _exists(store):
        return
    try:
        con = _connect(store)
    except sqlite3.Error:
        return
    try:
        if _schema_of(con) != SCHEMA_VERSION:
            return  # an older Index's tables: the next reader rebuilds it
        con.execute("BEGIN IMMEDIATE")
        try:
            if (
                version is not None
                and not con.execute(
                    "SELECT 1 FROM versions WHERE file = ?", (version.name,)
                ).fetchone()
            ):
                _index_version(con, version)
            touched = {
                FILE_OF[TagRow]: _notify_rows(con, TagRow, tags),
                FILE_OF[RecheckRow]: _notify_rows(con, RecheckRow, checks),
                FILE_OF[AliasRow]: _notify_rows(con, AliasRow, aliases),
            }
            if _agrees(con, store, touched):
                _write_meta(con, store, _ignored_of(con))
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    except sqlite3.Error:
        return
    finally:
        con.close()


def _ignored_of(con: sqlite3.Connection) -> int:
    row = con.execute("SELECT value FROM meta WHERE key = ?", (_IGNORED,)).fetchone()
    return int(row[0]) if row else 0


def _notify_rows(con: sqlite3.Connection, row_type: type[Row], rows: Sequence[Row]) -> bool:
    """Insert the rows the Index lacks, present by the same key as in the file (a Recheck row
    has none and is always new); whether the commit touched this table at all."""
    table = store_module.table_of(row_type)
    columns = store_module.columns(row_type)
    for row in rows:
        values = astuple(row)
        key = store_module.row_key(row)
        if key is not None:
            key_columns = columns[: len(key)]
            where = " AND ".join(f"{column} = ?" for column in key_columns)
            if con.execute(f"SELECT 1 FROM {table} WHERE {where}", key).fetchone():
                continue
        con.execute(f"INSERT INTO {table} VALUES({', '.join('?' * len(values))})", values)
    return bool(rows)


def _agrees(con: sqlite3.Connection, store: Path, touched: dict[str, bool]) -> bool:
    """Whether the Index, after this commit's inserts, describes the Store: every table the
    commit touched has as many rows as its file, `versions` and the `.md` files the rebuild
    ignored as many as there are `.md` files, and every watched file the commit did not touch
    is as `meta` recorded it."""
    recorded = dict(con.execute("SELECT key, value FROM meta").fetchall())
    if not recorded or recorded.get(_SCHEMA_KEY) != SCHEMA_VERSION:
        return False
    current = dict(_fingerprint(store))
    md_files = con.execute("SELECT count(*) FROM versions").fetchone()[0] + _ignored_of(con)
    if current["md_files"] != str(md_files):
        return False
    row_types = {name: row_type for row_type, name in FILE_OF.items()}
    for name in WATCHED_FILES:
        if touched.get(name):
            row_type = row_types[name]
            rows = len(store_module.read_rows(store, row_type))
            table = store_module.table_of(row_type)
            if con.execute(f"SELECT count(*) FROM {table}").fetchone()[0] != rows:
                return False
        elif any(recorded.get(f"{name}:{k}") != current[f"{name}:{k}"] for k in ("size", "mtime")):
            return False
    return True


# The Reader -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Hit:
    """`line` is the file's line of the first match in the Section (its first text line when no
    line holds a query word as written); `heading_line` its heading's (`None` before any)."""

    file: str
    line: int
    heading_line: int | None
    heading: str
    snippet: str
    url: str
    tags: list[str]


@dataclass(frozen=True)
class Scope:
    """Which latest Versions a search covers; `tags=None` means every Tag."""

    tags: Sequence[str] | None = None
    publisher: str | None = None
    authority: str | None = None


@dataclass(frozen=True)
class Revisit:
    """A work whose cited Source has a newer Version than the one it was written from."""

    work_id: str
    url: str
    old_sha256: str
    new_sha256: str


@dataclass(frozen=True)
class Summary:
    """What `status` reports from the Index."""

    versions: int
    sources: int
    tags: dict[str, int]
    oldest_fetched_at: str | None
    newest_fetched_at: str | None
    checks: dict[str, int]
    unknown_hosts: list[str]


@contextlib.contextmanager
def current(store: Path) -> Iterator[Reader | None]:
    """A Reader over a current Index, or `None` when the Index is missing, stale (its `meta`
    no longer describes the files) or unreadable, so the caller reads the files instead. Takes
    no lock and never rebuilds: the one protocol every lookup follows."""
    if not _exists(store):
        yield None
        return
    try:
        con = _connect(store)
    except sqlite3.Error:
        yield None
        return
    try:
        yield Reader(store, con) if _is_current(store, con) else None
    finally:
        con.close()


@contextlib.contextmanager
def ensured(store: Path, rules: Sequence[HostRule]) -> Iterator[Reader]:
    """A Reader over an Index brought up to date first (`ensure`, its rebuild reported on
    stderr): for the commands that may rebuild. It answers from what `ensure` found or built,
    without a second currency check."""
    report(ensure(store, rules))
    con = _connect(store)
    try:
        yield Reader(store, con)
    finally:
        con.close()


@dataclass(frozen=True)
class Reader:
    """Every question the Index answers, over the one connection `current` or `ensured`
    opened. Nothing else constructs one."""

    store: Path
    con: sqlite3.Connection

    def latest(self, url: str) -> VersionInfo | None:
        """The Latest Version of `url` from the view `latest` (the rule `history.latest`
        states), or `None` when the Store has none."""
        row = self.con.execute("SELECT file FROM latest WHERE url = ?", (url,)).fetchone()
        if row is None:
            return None
        return VersionInfo.read(self.store / row[0])

    def urls(self, prefix: str) -> list[str]:
        """Every Source's `url` that starts with `prefix`, sorted."""
        rows = self.con.execute(
            "SELECT DISTINCT url FROM versions WHERE substr(url, 1, ?) = ? ORDER BY url",
            (len(prefix), prefix),
        )
        return [url for (url,) in rows]

    def latest_in_scope(self, scope: Scope, prefix: str | None = None) -> list[VersionInfo]:
        """The latest Version of every Source in `scope` whose `url` starts with `prefix`, by
        url."""
        filters, args = _filters(scope)
        tag_filter, tag_args = _tag_filter(scope.tags)
        if prefix is not None:
            filters += " AND substr(l.url, 1, ?) = ?"
            args += [len(prefix), prefix]
        rows = self.con.execute(
            f"SELECT l.file FROM latest l WHERE 1{filters}{tag_filter} ORDER BY l.url",
            [*args, *tag_args],
        ).fetchall()
        return [VersionInfo.read(self.store / file) for (file,) in rows]

    def search(
        self, query: str, scope: Scope, *, limit: int, exact: bool
    ) -> tuple[list[Hit], int | None]:
        """The best `limit` Sections of the latest Versions in `scope`, and the count of
        distinct Sources the same query matches under other Tags (`None` when the scope is
        every Tag)."""
        con = self.con
        needle = unescape(query)
        if exact:
            match_from = "sections s"
            match_where = f"instr({_UNESCAPED_BODY}, ?) > 0"
            order = "s.file, s.ord"
            snippet = "s.body"
            match_args: list[object] = [needle]
            words = [needle]
        else:
            match_from = "sections_fts JOIN sections s ON s.id = sections_fts.rowid"
            match_where = "sections_fts MATCH ?"
            order = "bm25(sections_fts, 2.0, 1.0), s.file, s.ord"
            snippet = "snippet(sections_fts, 1, '[', ']', '…', 16)"
            match_args = [_fts_query(query)]
            words = [unescape(word).casefold() for word in query.split()]
        filters, filter_args = _filters(scope)
        tag_filter, tag_args = _tag_filter(scope.tags)
        rows = con.execute(
            f"SELECT s.file, s.line, s.heading_line, s.heading, s.body, {snippet}, l.url "
            f"FROM {match_from} "
            f"JOIN latest l ON l.file = s.file WHERE {match_where}{filters}{tag_filter} "
            f"ORDER BY {order} LIMIT ?",
            [*match_args, *filter_args, *tag_args, limit],
        ).fetchall()
        hits = [
            Hit(
                file=file,
                line=line + _match_offset(body, words, exact=exact),
                heading_line=heading_line,
                heading=heading,
                snippet=_snippet(unescape(text), needle) if exact else unescape(_one_line(text)),
                url=url,
                tags=_tags_of(con, url),
            )
            for file, line, heading_line, heading, body, text, url in rows
        ]
        other: int | None = None
        if scope.tags is not None:
            outside, outside_args = _tag_filter(scope.tags, inside=False)
            other = con.execute(
                f"SELECT count(DISTINCT l.url) FROM {match_from} "
                f"JOIN latest l ON l.file = s.file WHERE {match_where}{filters}{outside}",
                [*match_args, *filter_args, *outside_args],
            ).fetchone()[0]
        return hits, other

    def revisits(self) -> tuple[list[Revisit], list[str]]:
        """Every Citation whose Source changed since the work was written, and one warning per
        Citation of a `url` the Store has no Version of.

        The work was written from the Latest Version at `as_of` (`history.latest`), or from
        the oldest Version when `as_of` is absent or earlier than every Version. It is measured
        against the Latest Version now.
        """
        con = self.con
        citations = con.execute(
            "SELECT work_id, url, as_of FROM citations ORDER BY work_id, url"
        ).fetchall()
        found: list[Revisit] = []
        warnings: list[str] = []
        for work_id, url, as_of in citations:
            versions = con.execute(
                "SELECT fetched_at, sha256 FROM versions WHERE url = ? ORDER BY file", (url,)
            ).fetchall()
            if not versions:
                warnings.append(f"lorekeep: warning: {work_id} cites {url}, which is not stored")
                continue
            checks = con.execute(
                "SELECT checked_at, sha256 FROM checks WHERE url = ? ORDER BY rowid", (url,)
            ).fetchall()
            now = history.latest(versions, checks)
            assert now is not None, "a Source with Versions has a Latest Version"
            then = history.latest(versions, checks, as_of) if as_of else None
            written_from = then or min(versions, key=lambda version: version[0])[1]
            if written_from != now:
                found.append(Revisit(work_id, url, written_from, now))
        return found, warnings

    def summary(self) -> Summary:
        """Versions, Sources, Sources per Tag, the oldest and newest `fetched_at`, Rechecks per
        result, and the hosts no rule knew (a Version whose publisher is its url's host)."""
        con = self.con
        versions, sources, oldest, newest = con.execute(
            "SELECT count(*), count(DISTINCT url), min(fetched_at), max(fetched_at) FROM versions"
        ).fetchone()
        tags = dict(
            con.execute(
                "SELECT tag, count(DISTINCT url) FROM tags GROUP BY tag ORDER BY tag"
            ).fetchall()
        )
        checks: dict[str, int] = dict.fromkeys(store_module.RECHECK_RESULTS, 0)
        for result, count in con.execute("SELECT result, count(*) FROM checks GROUP BY result"):
            checks[result] = count
        hosts = {
            host
            for url, publisher in con.execute("SELECT DISTINCT url, publisher FROM versions")
            if (host := unknown_host(url, publisher))
        }
        return Summary(
            versions=versions,
            sources=sources,
            tags=tags,
            oldest_fetched_at=oldest,
            newest_fetched_at=newest,
            checks=checks,
            unknown_hosts=sorted(hosts),
        )


_UNESCAPED_BODY = r"replace(replace(s.body, '\_', '_'), '\*', '*')"
"""`s.body` with `unescape` applied, in SQL."""


def unescape(text: str) -> str:
    r"""Text with a converter's Markdown escapes of `_` and `*` undone, so `free\_gpu` reads as
    `free_gpu` (both sides of an `--exact` comparison go through it)."""
    return text.replace("\\_", "_").replace("\\*", "*")


def _match_offset(body: str, words: Sequence[str], *, exact: bool) -> int:
    """How many lines into `body` the first line holding one of `words` sits (as written for
    `--exact`, case-insensitively otherwise, after `unescape`); 0 when none does, as with a
    stemmed match."""
    for offset, line in enumerate(body.split("\n")):
        text = unescape(line) if exact else unescape(line).casefold()
        if any(word in text for word in words):
            return offset
    return 0


def _fts_query(query: str) -> str:
    """Every whitespace-separated word as a quoted phrase, so user input is never FTS5 syntax."""
    return " ".join('"' + word.replace('"', '""') + '"' for word in query.split())


def _filters(scope: Scope) -> tuple[str, list[object]]:
    sql, args = "", []
    if scope.publisher is not None:
        sql += " AND l.publisher = ?"
        args.append(scope.publisher)
    if scope.authority is not None:
        sql += " AND l.authority = ?"
        args.append(scope.authority)
    return sql, args


def _tag_filter(tags: Sequence[str] | None, *, inside: bool = True) -> tuple[str, list[object]]:
    if tags is None:
        return "", []
    marks = ", ".join("?" * len(tags))
    negation = "" if inside else "NOT "
    return f" AND l.url {negation}IN (SELECT url FROM tags WHERE tag IN ({marks}))", list(tags)


def _tags_of(con: sqlite3.Connection, url: str) -> list[str]:
    rows = con.execute("SELECT DISTINCT tag FROM tags WHERE url = ? ORDER BY tag", (url,))
    return [tag for (tag,) in rows]


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _snippet(body: str, needle: str, around: int = 60) -> str:
    """A snippet for an exact match: the text around its first occurrence, marked `[…]`."""
    at = body.find(needle)
    start, end = max(0, at - around), min(len(body), at + len(needle) + around)
    text = body[start:at] + "[" + needle + "]" + body[at + len(needle) : end]
    return ("…" if start else "") + _one_line(text) + ("…" if end < len(body) else "")
