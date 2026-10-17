"""One module per subcommand; each exposes `run(args, ctx) -> int`."""

from __future__ import annotations

from collections.abc import Sequence


def scope_tags(
    given: Sequence[str] | None, run_tag: str | None, *, everything: bool = False
) -> list[str] | None:
    """The Tags a scoped command covers: every Tag with `--all`; `--tag` repeated; else the
    Run's Tag; with none, every Tag (`None`)."""
    if everything:
        return None
    if given:
        return list(given)
    return [run_tag] if run_tag else None


def plural(count: int, word: str, plural_word: str | None = None) -> str:
    """`1 Version`, `2 Versions`, `0 aliases`: the count and the word it takes."""
    return f"{count} {word if count == 1 else plural_word or word + 's'}"
