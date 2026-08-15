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


def _meaningful(query: str) -> set[str]:
    return {t for t in _tokens(query) if t not in _STOPWORDS}


def matches_query(query: str, title: str, artist: str = "", label: str = "") -> bool:
    """Whether a result is a plausible hit for the query, or just store noise.

    Stores match loosely and return tracks that merely share a word or two with
    the query — a search for "Yoko - Y-Axis" surfaces every unrelated "Y-Axis"
    by other artists. We require the result to actually contain the query's
    meaningful words, tolerating roughly one unmatched word per four searched.
    A wrong track usually gives itself away by missing the artist name, so this
    drops the lookalikes while leaving minor gaps in long queries alone. When
    the query has no meaningful words, nothing is filtered (price sort decides).
    """
    q_tokens = _meaningful(query)
    if not q_tokens:
        return True

    haystack = set(_tokens(title)) | set(_tokens(artist)) | set(_tokens(label))
    missed = sum(1 for t in q_tokens if t not in haystack)
    return missed <= len(q_tokens) // 4


def relevance(query: str, title: str, artist: str = "", label: str = "") -> float:
    """Score how well a result matches the query, in [0, 1.5].

    coverage      — fraction of query words found anywhere in title/artist/label
    title bonus   — extra weight (up to 0.5) for query words that land in the
                    title, which is what distinguishes the requested track from
                    other songs by the same artist.

    Returns 0.0 when the query has no meaningful (non-stopword) words, so the
    caller falls back to its secondary sort (price).
    """
    q_tokens = _meaningful(query)
    if not q_tokens:
        return 0.0

    title_tokens = set(_tokens(title))
    haystack = title_tokens | set(_tokens(artist)) | set(_tokens(label))

    covered = sum(1 for t in q_tokens if t in haystack)
    title_hits = sum(1 for t in q_tokens if t in title_tokens)

    coverage = covered / len(q_tokens)
    title_bonus = title_hits / len(q_tokens)
    return coverage + 0.5 * title_bonus
