"""The fixed English stopword list a relaxed `search` drops from a question."""

from __future__ import annotations

import string

_LIST = """
    a about above after again against all am an and any are as at be because been before being
    below between both but by can could did do does doing down during each few for from further
    had has have having he her here hers herself him himself his how i if in into is it its itself
    just me more most my myself no nor not now of off on once only or other our ours ourselves out
    over own same she should so some such than that the their theirs them themselves then there
    these they this those through to too under until up very was we were what when where which
    while who whom whose why will with would you your yours yourself yourselves
"""

STOPWORDS = frozenset(_LIST.split())


def content_words(query: str) -> list[str]:
    """The words of `query` that are not stopwords, in order, each once (compared casefolded,
    punctuation at either end ignored)."""
    found: list[str] = []
    seen: set[str] = set()
    for word in query.split():
        key = word.strip(string.punctuation).casefold()
        if key and key not in STOPWORDS and key not in seen:
            seen.add(key)
            found.append(word)
    return found
