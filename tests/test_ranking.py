from __future__ import annotations

from ranking import relevance


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
