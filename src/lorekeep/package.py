"""The Store's `datapackage.json` (a Frictionless Data Package), generated from its files only.

`regenerate` is the only writer and runs under the Store lock: a resource for each CSV that exists,
typed by its columns, and one `sources` resource whose `data` is inline, one row per Version.
"""

from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from typing import Any

from lorekeep import store as store_module
from lorekeep.project import AUTHORITIES

PACKAGE_FILE = "datapackage.json"

# Every column the Store's CSVs are known to carry, typed; a column not listed here is a string.
# `status` holds `304` and `ReadTimeout` alike, and `as_of` a date or a timestamp, so both are
# strings.
_COLUMN_TYPES: dict[str, dict[str, dict[str, Any]]] = {
    store_module.TAGS_FILE: {"added_at": {"type": "datetime"}},
    store_module.CHECKS_FILE: {
        "checked_at": {"type": "datetime"},
        "result": {"type": "string", "constraints": {"enum": list(store_module.RECHECK_RESULTS)}},
        "status": {"type": "string"},
    },
    store_module.ALIASES_FILE: {"added_at": {"type": "datetime"}},
    store_module.CITATIONS_FILE: {"as_of": {"type": "string"}},
}

_SOURCES_SCHEMA: dict[str, Any] = {
    "fields": [
        {"name": "url", "type": "string"},
        {"name": "file", "type": "string"},
        {"name": "sha256", "type": "string"},
        {"name": "bytes", "type": "integer"},
        {"name": "fetched_at", "type": "datetime"},
        {"name": "publisher", "type": "string"},
        {"name": "authority", "type": "string", "constraints": {"enum": list(AUTHORITIES)}},
        {"name": "converter", "type": "string"},
    ]
}


def regenerate(store: Path) -> Path:
    """Write `datapackage.json` afresh from the Store's files, under the Store lock."""
    with store_module.lock(store):
        data = json.dumps(describe(store), indent=2, ensure_ascii=False) + "\n"
        target = store / PACKAGE_FILE
        tmp = target.with_name(f"{target.name}.tmp-{os.getpid()}")
        tmp.write_text(data, encoding="utf-8")
        os.replace(tmp, target)
        return target


def describe(store: Path) -> dict[str, Any]:
    resources = [_csv_resource(store / name) for name in _COLUMN_TYPES if (store / name).is_file()]
    resources.append(
        {
            "name": "sources",
            "profile": "tabular-data-resource",
            "data": [_source_row(info) for info in store_module.scan(store)],
            "schema": _SOURCES_SCHEMA,
        }
    )
    return {"name": _package_name(store), "profile": "data-package", "resources": resources}


def _csv_resource(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle), [])
    types = _COLUMN_TYPES[path.name]
    return {
        "name": path.stem,
        "path": path.name,
        "profile": "tabular-data-resource",
        "format": "csv",
        "mediatype": "text/csv",
        "encoding": "utf-8",
        "schema": {
            "fields": [
                {"name": column, **types.get(column, {"type": "string"})} for column in header
            ]
        },
    }


def _source_row(info: store_module.VersionInfo) -> dict[str, Any]:
    head = info.frontmatter
    return {
        "url": info.url,
        "file": info.path.name,
        "sha256": info.sha256,
        "bytes": info.path.stat().st_size,
        "fetched_at": info.fetched_at,
        "publisher": str(head["publisher"]),
        "authority": str(head["authority"]),
        "converter": str(head["converter"]),
    }


def _package_name(store: Path) -> str:
    """The Store folder's name in the form a package name must take (`^[-a-z0-9._/]+$`)."""
    return (
        re.sub(r"[^-a-z0-9._]+", "-", store.resolve().name.lower()).strip("-") or "lorekeep-store"
    )
