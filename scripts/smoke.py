"""The manual smoke test of lorekeep v1 against the live network; `pytest` never runs it.

It fetches one Twin, one static page and one page through the browser into a throw-away Store,
prints the converter of each, and restores one older generation of one object from the real
bucket with `restore --generation`, which proves the `#N` syntax the tests could only fake.

    uv sync --extra browser
    uv run python scripts/smoke.py --bucket <bucket> [--object <name in the bucket>]

It needs network access, Chromium for Crawl4AI and an authenticated `gcloud`; it reads the bucket
and writes nothing there. The Stores are temporary folders, removed when the script ends.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import re
import sys
import tempfile
from pathlib import Path

from lorekeep.cli import run
from lorekeep.edges import Edges

# One page per step of the cascade that matters live: the converter each must report.
PAGES = (
    ("Twin", "https://platform.claude.com/docs/en/build-with-claude/prompt-caching", "md-twin"),
    (
        "static page",
        "https://claude.termidy.com/learn/ccar-f/agentic-architecture/coordinator-and-subagents/",
        "trafilatura ",
    ),
    ("browser page", "https://milvus.io/docs/overview.md", "via crawl4ai"),
)
# Milvus answers a plain client now: this rule, in the throw-away Store only, sends it to the
# browser, so the browser step is proved whatever the host answers.
BROWSER_RULE = """
[[hosts]]
prefix = "milvus.io/docs/"
publisher = "milvus"
authority = "primary"
browser = true
"""
GENERATION = re.compile(r"^gs://[^/]+/(?P<name>[^#]+)#(?P<generation>\d+)$")


def lorekeep(argv: list[str], store: Path) -> tuple[int, str]:
    """Run one lorekeep command with the production edges; stderr passes through."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = run([*argv, "--store", str(store)], env={}, edges=Edges.production())
    return code, out.getvalue()


def gcloud(argv: list[str]) -> list[str]:
    done = Edges.production().runner.run(["gcloud", "storage", *argv])
    if done.returncode != 0:
        raise SystemExit(f"gcloud storage {' '.join(argv)} failed: {done.stderr.strip()}")
    return done.stdout.split()


def fetch_pages(store: Path) -> bool:
    passed = True
    for what, url, expected in PAGES:
        code, out = lorekeep(["get", url, "--tag", "smoke", "--json"], store)
        if code != 0:
            print(f"FAIL {what}: get exited {code} for {url}")
            passed = False
            continue
        version = json.loads(out)
        ok = expected in version["converter"]
        print(f"{'ok  ' if ok else 'FAIL'} {what}: {version['converter']}  ({version['url']})")
        passed = passed and ok
    return passed


def restore_a_generation(store: Path, bucket: str, name: str | None) -> bool:
    """Restore into a Store of its own, so a page fetched above never blocks it."""
    if name is None:
        objects = [line for line in gcloud(["ls", f"gs://{bucket}"]) if line.endswith(".md")]
        if not objects:
            print(f"FAIL restore: no Version in gs://{bucket}")
            return False
        name = objects[0].removeprefix(f"gs://{bucket}/")
    generations = [
        found
        for line in gcloud(["ls", "--all-versions", f"gs://{bucket}/{name}"])
        if (found := GENERATION.match(line))
    ]
    if not generations:
        print(f"FAIL restore: gs://{bucket}/{name} lists no generation")
        return False
    generation = generations[0]["generation"]
    code, out = lorekeep(["restore", name, "--generation", generation], store)
    restored = store / name
    if code != 0 or not restored.is_file():
        print(f"FAIL restore: restore {name} --generation {generation} exited {code}")
        return False
    digest = hashlib.sha256(restored.read_bytes()).hexdigest()[:8]
    print(f"ok   restore: {name}#{generation} -> {out.strip()} (sha256 {digest}…)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="The manual smoke test of lorekeep v1 against the live network."
    )
    parser.add_argument("--bucket", required=True, help="the Project's bucket, read only")
    parser.add_argument("--object", help="the object to restore (default: the first Version)")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="lorekeep-smoke-") as folder:
        pages, restores = Path(folder) / "pages", Path(folder) / "restores"
        for store in (pages, restores):
            store.mkdir()
            (store / "lorekeep.toml").write_text(f'bucket = "{args.bucket}"\n')
        with (pages / "lorekeep.toml").open("a") as config:
            config.write(BROWSER_RULE)
        fetched = fetch_pages(pages)
        restored = restore_a_generation(restores, args.bucket, args.object)
    print("smoke test passed" if fetched and restored else "smoke test FAILED")
    return 0 if fetched and restored else 1


if __name__ == "__main__":
    sys.exit(main())
