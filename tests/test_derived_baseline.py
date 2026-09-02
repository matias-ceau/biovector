"""Tests for official baseline eligibility (DESIGN.md section 5.7).

The official EWRM baseline must be built only from sets with reps <= 12
(Epley validity zone). Per-set e1RM is kept for every set; long sets are
scored against the baseline but can never raise it. Exercises with no short
set at all fall back to an all-sets baseline with confidence "low".
"""

from __future__ import annotations

import json

import pytest

from biovector.derived import BASELINE_MAX_REPS, DerivedDataPipeline

EXERCISES = {
    "exercises": [
        {
            "id": "U99.9",
            "name": "Test Curl",
            "short": "tc",
            "delta": 0.6,
            "rho": 0.0,
            "theta": 0.0,
            "type": "Barbell",
        },
        {
            "id": "G99.9",
            "name": "Test Grip",
            "short": "tg",
            "delta": 0.1,
            "rho": 0.0,
            "theta": 0.0,
            "type": "Barbell",
        },
    ]
}


def _day(n: int) -> float:
    """Timestamp n days after an arbitrary epoch, spaced far enough apart."""
    return 1_700_000_000 + n * 86_400


def _make_data_dir(tmp_path, sets: list[dict]) -> None:
    user = tmp_path / "user"
    ref = tmp_path / "reference"
    user.mkdir(parents=True)
    ref.mkdir(parents=True)
    (user / "sets.json").write_text(json.dumps({"sets": sets}))
    (user / "sessions.json").write_text(json.dumps({"sessions": []}))
    (user / "bodyweight.json").write_text(
        json.dumps({"measurements": [{"timestamp": 0, "weight_kg": 85.0}]})
    )
    (ref / "exercises.json").write_text(json.dumps(EXERCISES))


def _run(tmp_path, sets: list[dict]) -> DerivedDataPipeline:
    _make_data_dir(tmp_path, sets)
    p = DerivedDataPipeline(data_dir=str(tmp_path))
    p.load_data()
    p.classify_exercises()
    p.pass1_basic_enrichment()
    p.pass2_smoothed_1rm()
    p.pass3_intensity()
    return p


def test_baseline_max_reps_constant():
    assert BASELINE_MAX_REPS == 12


def test_long_set_does_not_raise_baseline(tmp_path):
    """A 20-rep set (e1RM inflated by Epley) must not enter the baseline."""
    sets = [
        {"timestamp": _day(1), "exercise_name": "Test Curl", "weight": 50.0,
         "reps": 20, "session_name": "S1", "notes": ""},
        {"timestamp": _day(2), "exercise_name": "Test Curl", "weight": 40.0,
         "reps": 8, "session_name": "S2", "notes": ""},
        {"timestamp": _day(3), "exercise_name": "Test Curl", "weight": 42.5,
         "reps": 8, "session_name": "S3", "notes": ""},
    ]
    p = _run(tmp_path, sets)
    s1, s2, s3 = p.enriched_sets

    # Habitual e1RM preserved on the long set (50 * (1 + 20/30) = 83.3)
    assert s1["pred_1rm"] == 83.3
    # But no official baseline existed at that time -> no intensity
    assert s1["smoothed_1rm"] == 0.0
    assert s1["h"] is None

    # Short sets build the baseline: 50.7 then 53.8
    assert s2["pred_1rm"] == 50.7
    assert s2["smoothed_1rm"] == 50.7
    assert s3["pred_1rm"] == 53.8
    # The running max must come from short sets only — never from the 83.3
    assert s3["smoothed_1rm"] == 53.8
    assert s3["smoothed_confidence"] == "high"  # 3 sessions, no fallback
    assert "baseline_fallback" not in s1


def test_long_set_scored_against_official_baseline(tmp_path):
    """A long set keeps its habitual e1RM and can be a hard set,
    but is scored against the short-set baseline it cannot raise."""
    sets = [
        {"timestamp": _day(1), "exercise_name": "Test Curl", "weight": 60.0,
         "reps": 6, "session_name": "S1", "notes": ""},
        {"timestamp": _day(2), "exercise_name": "Test Curl", "weight": 30.0,
         "reps": 20, "session_name": "S2", "notes": ""},
    ]
    p = _run(tmp_path, sets)
    s1, s2 = p.enriched_sets

    # Official baseline from the short set: 60 * (1 + 6/30) = 72.0
    assert s2["smoothed_1rm"] == 72.0
    # Habitual e1RM of the long set kept: 30 * (1 + 20/30) = 50.0
    assert s2["pred_1rm"] == 50.0
    # The long set is still scored -> can be a hard set
    assert s2["h"] is not None
    assert s2["smoothed_confidence"] == "low"  # only 2 sessions
    assert "baseline_fallback" not in s2


def test_fallback_when_no_short_sets(tmp_path):
    """An exercise with only long sets falls back to an all-sets baseline,
    forced to confidence "low", flagged baseline_fallback — but its sets
    are still scored (a long set can be a hard set)."""
    sets = [
        {"timestamp": _day(1), "exercise_name": "Test Grip", "weight": 20.0,
         "reps": 15, "session_name": "S1", "notes": ""},
        {"timestamp": _day(2), "exercise_name": "Test Grip", "weight": 21.0,
         "reps": 15, "session_name": "S2", "notes": ""},
    ]
    p = _run(tmp_path, sets)
    s1, s2 = p.enriched_sets

    # Fallback baseline from ALL sets: 21 * (1 + 15/30) = 31.5
    assert s2["smoothed_1rm"] == pytest.approx(31.5, abs=0.1)
    assert s2["smoothed_confidence"] == "low"
    assert s2.get("baseline_fallback") is True
    # Still scored: intensity and h exist
    assert s2["h"] is not None
    assert s2["is_hard_set"] is True  # self-referential max -> intensity ~1.0
