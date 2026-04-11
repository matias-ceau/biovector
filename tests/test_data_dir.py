"""Tests for the new JSON-backed biovector core."""

import sys
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def test_biovector_loads_data():
    from biovector.core import Biovector
    bv = Biovector()
    assert len(bv.sets) > 0
    assert len(bv.exercises) > 0
    assert len(bv.sessions) > 0


def test_sets_have_core_fields():
    from biovector.core import Biovector
    bv = Biovector()
    s = bv.sets[0]
    assert "timestamp" in s
    assert "exercise_name" in s
    assert "weight" in s
    assert "reps" in s


def test_exercise_lookup():
    from biovector.core import Biovector
    bv = Biovector()
    ex = bv.get_exercise("Squat")
    assert ex is not None
    assert ex["id"] == "S00"
    assert ex["delta"] > 0


def test_exercise_lookup_by_short():
    from biovector.core import Biovector
    bv = Biovector()
    ex = bv.get_exercise("sq")
    assert ex is not None
    assert ex["name"] == "Squat"


def test_exercise_lookup_by_id():
    from biovector.core import Biovector
    bv = Biovector()
    ex = bv.get_exercise("S00")
    assert ex is not None
    assert ex["name"] == "Squat"


def test_epley_formula():
    from biovector.core import epley
    assert epley(100, 10) == 100 * (1 + 10 / 30)


def test_logistic_hard_set():
    from biovector.core import logistic
    # At 90% intensity, should be close to 1.05
    assert logistic(0.9) > 1.0
    # At 50% intensity, should be close to 0
    assert logistic(0.5) < 0.01


def test_compute_set_metrics():
    from biovector.core import Biovector
    bv = Biovector()
    s = bv.sets[0]
    metrics = bv.compute_set_metrics(s)
    assert "pred_1rm" in metrics
    assert "load" in metrics
    assert metrics["pred_1rm"] > 0


def test_exercise_1rm_history():
    from biovector.core import Biovector
    bv = Biovector()
    history = bv.exercise_1rm_history("Squat")
    assert len(history) > 0
    assert "pred_1rm" in history[0]
    assert "best_1rm" in history[0]


def test_list_exercises_filter():
    from biovector.core import Biovector
    bv = Biovector()
    barbells = bv.list_exercises(category="Barbell")
    assert len(barbells) > 0
    assert all(e["type"] == "Barbell" for e in barbells)


def test_list_exercises_search():
    from biovector.core import Biovector
    bv = Biovector()
    results = bv.list_exercises(search="squat")
    assert len(results) > 0
