"""The Index: `sources.db`, derived from the Store's files.

It holds every Version's Provenance, the rows of `tags.csv`, `checks.csv` and `aliases.csv`, and
the Versions' Sections with an FTS5 table over them. It is rebuilt in place, in one transaction,
under the Store lock; a lookup reads it without the lock and only when it is current, which the
`meta` table recorded at build time says. Ticket 14 fills the commit notification.
"""

from __future__ import annotations

import csv
import re
import sqlite3
import sys
from collections.abc import Iterator, Sequence
from dataclasses import astuple, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from lorekeep import frontmatter
from lorekeep import store as store_module
from lorekeep.project import load_project
from lorekeep.urls import normalise

if TYPE_CHECKING:
    from lorekeep.store import AliasRow, CheckRow, TagRow, VersionInfo

INDEX_FILE = "sources.db"
CITATIONS_FILE = "citations.csv"
SECTION_BYTES = 4096
WATCHED_FILES = ("tags.csv", "checks.csv", "aliases.csv", "citations.csv")

VERSION_COLUMNS = (
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
    "origin",
)
ORIGINAL_COLUMNS = ("url", "mediatype", "sha256", "stored")

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS versions(
  file TEXT PRIMARY KEY,
  {", ".join(f"{column} TEXT" for column in VERSION_COLUMNS)},
  {", ".join(f"original_{column} TEXT" for column in ORIGINAL_COLUMNS)}
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
  line INTEGER NOT NULL,
  body TEXT NOT NULL,
  ord INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS sections_file ON sections(file);
CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts USING fts5(
  heading, body, content='sections', content_rowid='id', tokenize='porter unicode61'
);
-- The latest Version of each Source: the one its latest `checks.csv` row names, else the newest
-- `fetched_at`; the same answer as the Store's scan.
CREATE VIEW IF NOT EXISTS latest AS
SELECT v.* FROM versions v
WHERE v.file = (
  SELECT w.file FROM versions w
  WHERE w.url = v.url
  ORDER BY w.sha256 = (
    SELECT c.sha256 FROM checks c
    WHERE c.url = v.url AND c.sha256 != ''
    ORDER BY c.checked_at DESC LIMIT 1
  ) DESC, w.fetched_at DESC, w.file
  LIMIT 1
);
"""


def connect(store: Path) -> sqlite3.Connection:
    """A connection to the Store's Index in WAL mode with a busy timeout; explicit transactions."""
    con = sqlite3.connect(store / INDEX_FILE, timeout=30.0, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def exists(store: Path) -> bool:
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


def rebuild(store: Path) -> Counts:
    """Empty and refill every table from the Store's files, in place, under the Store lock."""
    with store_module.lock(store):
        return _rebuild_locked(store)


def ensure(store: Path) -> Counts | None:
    """Bring the Index up to date before a reader queries it: compare `meta` with the files
    without any lock; only when the file is missing or stale take the Store lock, compare again
    and rebuild in place. Returns the rebuild's counts, or `None` when the Index was current, so
    six readers finding none produce one build and a query on a current Index never waits."""
    if _looks_current(store):
        return None
    with store_module.lock(store):
        if _looks_current(store):
            return None
        return _rebuild_locked(store)


def report(counts: Counts | None) -> None:
    """Print a rebuild's warnings to stderr; nothing when there was no rebuild."""
    if counts is not None:
        for warning in counts.warnings:
            print(warning, file=sys.stderr)


def _looks_current(store: Path) -> bool:
    if not exists(store):
        return False
    try:
        con = sqlite3.connect(store / INDEX_FILE, timeout=30.0, isolation_level=None)
    except sqlite3.Error:
        return False
    try:
        return is_current(store, con)
    finally:
        con.close()


def _rebuild_locked(store: Path) -> Counts:
    con = connect(store)
    try:
        con.executescript(SCHEMA)
        con.execute("BEGIN IMMEDIATE")
        try:
            tables = ("versions", "tags", "checks", "aliases", "citations", "sections", "meta")
            for table in tables:
                con.execute(f"DELETE FROM {table}")
            con.execute("INSERT INTO sections_fts(sections_fts) VALUES('delete-all')")
            versions = sections = 0
            for path in sorted(store.glob("*.md")):
                data = path.read_bytes()
                head, body = frontmatter.parse(data)
                _insert_version(con, path.name, head)
                versions += 1
                first_line = data[: len(data) - len(body)].count(b"\n") + 1
                text = body.decode("utf-8", errors="replace")
                rows = [
                    (path.name, section.heading, section.line, section.body, order)
                    for order, section in enumerate(split_sections(text, first_line))
                ]
                con.executemany(
                    "INSERT INTO sections(file, heading, line, body, ord) VALUES(?, ?, ?, ?, ?)",
                    rows,
                )
                sections += len(rows)
            tags = _insert_rows(con, "tags", store_module.read_rows(store, store_module.TagRow))
            checks = _insert_rows(
                con, "checks", store_module.read_rows(store, store_module.CheckRow)
            )
            aliases = _insert_rows(
                con, "aliases", store_module.read_rows(store, store_module.AliasRow)
            )
            cited, warnings = read_citations(store)
            con.executemany("INSERT INTO citations VALUES(?, ?, ?)", cited)
            con.execute("INSERT INTO sections_fts(sections_fts) VALUES('rebuild')")
            con.executemany("INSERT INTO meta(key, value) VALUES(?, ?)", fingerprint(store))
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    finally:
        con.close()
    return Counts(versions, sections, tags, checks, aliases, len(cited), tuple(warnings))


def read_citations(store: Path) -> tuple[list[tuple[str, str, str | None]], list[str]]:
    """The rows of `citations.csv` (`work_id, url[, as_of]`), written by the consuming Project:
    `url` normalised and Twin-reduced like a request, `as_of` an ISO 8601 date or timestamp
    brought to UTC `YYYY-MM-DDTHH:MM:SSZ` (a bare date means the end of that day, so a work
    written that day is measured against the Version current then) or `None` when absent. A
    row that cannot be read is left out and named with its line number in the warnings."""
    path = store / CITATIONS_FILE
    if not path.is_file():
        return [], []
    rules = load_project(store).hosts
    rows: list[tuple[str, str, str | None]] = []
    warnings: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header is None:
            return [], []
        if [column.strip() for column in header[:2]] != ["work_id", "url"]:
            return [], [f"warning: {CITATIONS_FILE} line 1: the header is not work_id,url[,as_of]"]
        for row in reader:
            line = reader.line_num
            cells = [cell.strip() for cell in row]
            if not any(cells):
                continue
            if len(cells) < 2 or not cells[0] or not cells[1]:
                warnings.append(
                    f"warning: {CITATIONS_FILE} line {line}: expected work_id,url[,as_of]"
                )
                continue
            as_of = cells[2] if len(cells) > 2 and cells[2] else None
            try:
                when = _as_of(as_of)
            except ValueError:
                warnings.append(
                    f"warning: {CITATIONS_FILE} line {line}: as_of {as_of!r} is not an ISO 8601 "
                    "date or timestamp"
                )
                continue
            rows.append((cells[0], normalise(cells[1], rules), when))
    return rows, warnings


def _as_of(text: str | None) -> str | None:
    if text is None:
        return None
    parsed = datetime.fromisoformat(text)
    if len(text) == 10:
        parsed = parsed.replace(hour=23, minute=59, second=59)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _insert_version(con: sqlite3.Connection, file: str, head: dict[str, object]) -> None:
    original = head.get("original")
    original = original if isinstance(original, dict) else {}
    values = [file]
    values += [_text(head.get(column)) for column in VERSION_COLUMNS]
    values += [_text(original.get(column)) for column in ORIGINAL_COLUMNS]
    marks = ", ".join("?" * len(values))
    con.execute(f"INSERT INTO versions VALUES({marks})", values)


def _text(value: object) -> str | None:
    return None if value is None else str(value)


def _insert_rows(
    con: sqlite3.Connection, table: str, rows: Sequence[TagRow | CheckRow | AliasRow]
) -> int:
    if rows:
        marks = ", ".join("?" * len(astuple(rows[0])))
        con.executemany(f"INSERT INTO {table} VALUES({marks})", [astuple(row) for row in rows])
    return len(rows)


def fingerprint(store: Path) -> list[tuple[str, str]]:
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


def is_current(store: Path, con: sqlite3.Connection) -> bool:
    """Whether the Index's `meta` still describes the Store's files; no lock is taken."""
    try:
        recorded = dict(con.execute("SELECT key, value FROM meta").fetchall())
    except sqlite3.Error:
        return False
    return bool(recorded) and recorded == dict(fingerprint(store))


# Sections ----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Section:
    heading: str
    line: int
    body: str


_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)[ \t#]*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def split_sections(text: str, first_line: int = 1) -> Iterator[Section]:
    """The text under each Markdown heading, with its heading path (`A > B`) and the line its
    heading sits on (`first_line` is the body's first line in the file). A Section over
    `SECTION_BYTES` is cut again at paragraph boundaries; a code fence is never cut."""
    path: list[tuple[int, str]] = []
    heading, start, lines = "", first_line, []
    fence: str | None = None
    for number, line in enumerate(text.splitlines(), start=first_line):
        opener = _FENCE.match(line)
        if fence is not None:
            if opener and opener.group(1)[0] == fence[0] and len(opener.group(1)) >= len(fence):
                fence = None
        elif opener:
            fence = opener.group(1)
        else:
            match = _HEADING.match(line)
            if match:
                yield from _slices(heading, start, lines)
                level = len(match.group(1))
                path = [(lvl, name) for lvl, name in path if lvl < level]
                path.append((level, match.group(2).strip()))
                heading = " > ".join(name for _, name in path)
                start, lines = number, []
                continue
        if not lines and heading == "" and not line.strip():
            start = number + 1
            continue
        lines.append((number, line))
    yield from _slices(heading, start, lines)


def _slices(heading: str, start: int, lines: list[tuple[int, str]]) -> Iterator[Section]:
    """Cut one heading's text into Sections of at most `SECTION_BYTES` at paragraph boundaries.

    A paragraph (or a whole code fence) larger than the limit is cut at line boundaries when it
    is prose and kept whole when it is a fence."""
    blocks = _blocks(lines)
    if not any(text.strip() for _, text in lines):
        return
    current: list[tuple[int, str]] = []
    size = 0
    line = start
    for block in blocks:
        block_size = sum(len(text.encode()) + 1 for _, text in block)
        if current and size + block_size > SECTION_BYTES:
            yield Section(heading, line, _join(current))
            current, size, line = [], 0, block[0][0]
        if block_size > SECTION_BYTES and not _FENCE.match(block[0][1]):
            for number, text in block:
                text_size = len(text.encode()) + 1
                if current and size + text_size > SECTION_BYTES:
                    yield Section(heading, line, _join(current))
                    current, size, line = [], 0, number
                current.append((number, text))
                size += text_size
            continue
        current += block
        size += block_size
    if any(text.strip() for _, text in current):
        yield Section(heading, line, _join(current))


def _blocks(lines: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    """Paragraphs and code fences, each with the blank lines before the next one."""
    blocks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    fence: str | None = None
    for number, text in lines:
        opener = _FENCE.match(text)
        if fence is not None:
            current.append((number, text))
            if opener and opener.group(1)[0] == fence[0] and len(opener.group(1)) >= len(fence):
                fence = None
            continue
        if opener:
            if any(t.strip() for _, t in current):
                blocks.append(current)
                current = []
            fence = opener.group(1)
            current.append((number, text))
            continue
        if not text.strip() and any(t.strip() for _, t in current):
            current.append((number, text))
            blocks.append(current)
            current = []
            continue
        current.append((number, text))
    if current:
        blocks.append(current)
    return blocks


def _join(lines: list[tuple[int, str]]) -> str:
    return "\n".join(text for _, text in lines).strip("\n")


# Lookup and notification -------------------------------------------------------------------------


class Unanswered:
    """What `lookup` returns when the Index cannot answer: missing, stale or unreadable."""


UNANSWERED = Unanswered()


def lookup(store: Path, url: str) -> VersionInfo | Unanswered | None:
    """The latest Version of `url` from a current Index, `None` when a current Index has none,
    and `UNANSWERED` when the Index cannot say, so the caller scans. Takes no lock and never
    rebuilds."""
    if not exists(store):
        return UNANSWERED
    try:
        con = sqlite3.connect(store / INDEX_FILE, timeout=30.0, isolation_level=None)
    except sqlite3.Error:
        return UNANSWERED
    try:
        if not is_current(store, con):
            return UNANSWERED
        row = con.execute("SELECT file FROM latest WHERE url = ?", (url,)).fetchone()
    except sqlite3.Error:
        return UNANSWERED
    finally:
        con.close()
    if row is None:
        return None
    path = store / row[0]
    if not path.is_file():
        return UNANSWERED
    return store_module.VersionInfo(path, store_module.read_head(path))


def notify(
    store: Path,
    *,
    version: Path | None,
    tags: Sequence[TagRow],
    checks: Sequence[CheckRow],
    aliases: Sequence[AliasRow],
) -> None:
    """Tell the Index what a commit wrote, in one small transaction, under the Store lock.

    A missing Index is left missing (a commit never builds one). The Version and the rows not
    already in the Index are inserted; then, when every table agrees with the files the commit
    touched and no file it did not touch has changed, `meta` is brought up to date in the same
    transaction, so the commit never looks like staleness. Otherwise `meta` is left as it was and
    the Index stays stale for the next reader to rebuild.
    """
    if not exists(store):
        return
    try:
        con = connect(store)
    except sqlite3.Error:
        return
    try:
        con.execute("BEGIN IMMEDIATE")
        try:
            if version is not None:
                _index_version(con, store, version)
            touched = {
                "tags.csv": _notify_rows(con, "tags", tags),
                "checks.csv": _notify_rows(con, "checks", checks),
                "aliases.csv": _notify_rows(con, "aliases", aliases),
            }
            if _agrees(con, store, touched):
                con.execute("DELETE FROM meta")
                con.executemany("INSERT INTO meta(key, value) VALUES(?, ?)", fingerprint(store))
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    except sqlite3.Error:
        return
    finally:
        con.close()


def _index_version(con: sqlite3.Connection, store: Path, path: Path) -> None:
    """Insert one Version and its Sections when the Index has no row for its file."""
    if con.execute("SELECT 1 FROM versions WHERE file = ?", (path.name,)).fetchone():
        return
    data = path.read_bytes()
    head, body = frontmatter.parse(data)
    _insert_version(con, path.name, head)
    first_line = data[: len(data) - len(body)].count(b"\n") + 1
    for order, section in enumerate(
        split_sections(body.decode("utf-8", errors="replace"), first_line)
    ):
        cursor = con.execute(
            "INSERT INTO sections(file, heading, line, body, ord) VALUES(?, ?, ?, ?, ?)",
            (path.name, section.heading, section.line, section.body, order),
        )
        con.execute(
            "INSERT INTO sections_fts(rowid, heading, body) VALUES(?, ?, ?)",
            (cursor.lastrowid, section.heading, section.body),
        )


def _notify_rows(
    con: sqlite3.Connection, table: str, rows: Sequence[TagRow | CheckRow | AliasRow]
) -> bool:
    """Insert the rows the Index lacks; whether the commit touched this table at all."""
    for row in rows:
        values = astuple(row)
        key = {"tags": ("url", "tag"), "aliases": ("alias", "url")}.get(table)
        columns = _COLUMNS_OF[table]
        wanted = columns if key is None else key
        where = " AND ".join(f"{column} = ?" for column in wanted)
        args = [values[columns.index(column)] for column in wanted]
        if con.execute(f"SELECT 1 FROM {table} WHERE {where}", args).fetchone():
            continue
        con.execute(f"INSERT INTO {table} VALUES({', '.join('?' * len(values))})", values)
    return bool(rows)


_COLUMNS_OF = {
    "tags": ("url", "tag", "added_at"),
    "checks": ("url", "checked_at", "result", "status", "sha256"),
    "aliases": ("alias", "url", "added_at"),
}


def _agrees(con: sqlite3.Connection, store: Path, touched: dict[str, bool]) -> bool:
    """Whether the Index, after this commit's inserts, describes the Store: every table the
    commit touched has as many rows as its file, `versions` as many as there are `.md` files,
    and every watched file the commit did not touch is as `meta` recorded it."""
    recorded = dict(con.execute("SELECT key, value FROM meta").fetchall())
    if not recorded:
        return False
    current = dict(fingerprint(store))
    md_files = con.execute("SELECT count(*) FROM versions").fetchone()[0]
    if current["md_files"] != str(md_files):
        return False
    for name in WATCHED_FILES:
        if touched.get(name):
            row_type = {
                "tags.csv": store_module.TagRow,
                "checks.csv": store_module.CheckRow,
                "aliases.csv": store_module.AliasRow,
            }[name]
            rows = len(store_module.read_rows(store, row_type))
            table = name.removesuffix(".csv")
            if con.execute(f"SELECT count(*) FROM {table}").fetchone()[0] != rows:
                return False
        elif any(recorded.get(f"{name}:{k}") != current[f"{name}:{k}"] for k in ("size", "mtime")):
            return False
    return True


# Search ------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Hit:
    file: str
    line: int
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


def fts_query(query: str) -> str:
    """Every whitespace-separated word as a quoted phrase, so user input is never FTS5 syntax."""
    return " ".join('"' + word.replace('"', '""') + '"' for word in query.split())


def search(
    store: Path, query: str, scope: Scope, *, limit: int, exact: bool
) -> tuple[list[Hit], int | None]:
    """The best `limit` Sections of the latest Versions in `scope`, and the count of distinct
    Sources the same query matches under other Tags (`None` when the scope is every Tag)."""
    con = connect(store)
    try:
        if exact:
            match_from = "sections s"
            match_where = "instr(s.body, ?) > 0"
            order = "s.file, s.ord"
            snippet = "s.body"
            match_args: list[object] = [query]
        else:
            match_from = "sections_fts JOIN sections s ON s.id = sections_fts.rowid"
            match_where = "sections_fts MATCH ?"
            order = "bm25(sections_fts, 2.0, 1.0), s.file, s.ord"
            snippet = "snippet(sections_fts, 1, '[', ']', '…', 16)"
            match_args = [fts_query(query)]
        filters, filter_args = _filters(scope)
        tag_filter, tag_args = _tag_filter(scope.tags)
        rows = con.execute(
            f"SELECT s.file, s.line, s.heading, {snippet}, l.url FROM {match_from} "
            f"JOIN latest l ON l.file = s.file WHERE {match_where}{filters}{tag_filter} "
            f"ORDER BY {order} LIMIT ?",
            [*match_args, *filter_args, *tag_args, limit],
        ).fetchall()
        hits = [
            Hit(
                file=file,
                line=line,
                heading=heading,
                snippet=_snippet(text, query) if exact else _one_line(text),
                url=url,
                tags=_tags_of(con, url),
            )
            for file, line, heading, text, url in rows
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
    finally:
        con.close()


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
