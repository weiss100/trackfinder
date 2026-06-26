"""Relevance scoring for store search results.

Stores match loosely — a search for "Of The Trees - The Owl Song" returns
every track by that artist, so sorting purely by price buries the track the
user actually asked for. We score each result by how many of the query's
meaningful words it contains, rewarding matches in the *title* (the real track
name) over matches in the artist, and let the caller use price only as a
tiebreaker between equally relevant hits.
"""
from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[0-9a-z]+")

# Words too common to carry signal in a music query. Kept deliberately small:
# anything that could be part of a real track name (e.g. "remix") stays in.
_STOPWORDS = frozenset({"the", "a", "an", "of", "and", "feat", "ft", "featuring", "with"})


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def relevance(query: str, title: str, artist: str = "", label: str = "") -> float:
    """Score how well a result matches the query, in [0, 1.5].

    coverage      — fraction of query words found anywhere in title/artist/label
    title bonus   — extra weight (up to 0.5) for query words that land in the
                    title, which is what distinguishes the requested track from
                    other songs by the same artist.

    Returns 0.0 when the query has no meaningful (non-stopword) words, so the
    caller falls back to its secondary sort (price).
    """
    q_tokens = {t for t in _tokens(query) if t not in _STOPWORDS}
    if not q_tokens:
        return 0.0

    title_tokens = set(_tokens(title))
    haystack = title_tokens | set(_tokens(artist)) | set(_tokens(label))

    covered = sum(1 for t in q_tokens if t in haystack)
    title_hits = sum(1 for t in q_tokens if t in title_tokens)

    coverage = covered / len(q_tokens)
    title_bonus = title_hits / len(q_tokens)
    return coverage + 0.5 * title_bonus
