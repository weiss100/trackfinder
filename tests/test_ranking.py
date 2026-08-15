from __future__ import annotations

from ranking import matches_query, relevance


def test_exact_title_outranks_same_artist_other_song():
    q = "Of The Trees The Owl Song"
    owl = relevance(q, "The Owl Song", "Of The Trees")
    other = relevance(q, "Muscaria", "Of The Trees")
    assert owl > other


def test_title_match_beats_artist_only_match():
    q = "Of The Trees The Owl Song"
    title_match = relevance(q, "The Owl Song", "Some DJ")
    artist_only = relevance(q, "Hieroglyph", "Of The Trees")
    assert title_match > artist_only


def test_no_meaningful_tokens_scores_zero():
    # Pure stopwords carry no signal -> caller falls back to price sort.
    assert relevance("the of and", "Anything", "Whoever") == 0.0


def test_unrelated_result_scores_below_partial_match():
    q = "daft punk one more time"
    match = relevance(q, "One More Time", "Daft Punk")
    miss = relevance(q, "Random Track", "Other Artist")
    assert match > miss
    assert miss == 0.0


def test_label_contributes_to_coverage_but_not_title_bonus():
    q = "memory palace dubstep"
    in_label = relevance(q, "Some Title", "Some Artist", "Memory Palace")
    nowhere = relevance(q, "Some Title", "Some Artist", "Other Label")
    assert in_label > nowhere


def test_matches_query_keeps_full_match_drops_lookalike():
    q = "Yoko Y-Axis"
    # Right title, wrong artist: the missing "yoko" gives it away.
    assert not matches_query(q, "Y-Axis", "Phil Berg")
    # The actual track matches every word.
    assert matches_query(q, "Y-Axis", "Yoko")


def test_matches_query_tolerates_one_miss_in_long_query():
    q = "daft punk one more time harder"  # 6 meaningful tokens -> 1 miss allowed
    assert matches_query(q, "One More Time", "Daft Punk")  # "harder" missing
    # Two missing words is too many for this length.
    assert not matches_query(q, "One More Time", "Someone")


def test_matches_query_requires_all_words_for_short_query():
    assert not matches_query("hollow ground", "Hollow Halls", "Whoever")
    assert matches_query("hollow ground", "Hollow Ground", "Whoever")


def test_matches_query_keeps_everything_when_query_has_no_signal():
    # Pure stopwords carry no signal -> don't filter; price sort decides.
    assert matches_query("the of and", "Anything", "Whoever")
