"""Biovector core library — data access and metric calculations.

All data is stored as JSON in the repository:
- data/user/sets.json       — core set records
- data/user/sessions.json   — auto-generated session groupings
- data/user/bodyweight.json — bodyweight time-series
- data/reference/exercises.json — exercise definitions with coefficients
"""

from __future__ import annotations

import json
import math
import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_USER = REPO_ROOT / "data" / "user"
DATA_REF = REPO_ROOT / "data" / "reference"


def _load_json(path: Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def _save_json(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Pure math helpers
# ---------------------------------------------------------------------------

def epley(weight: float, reps: float) -> float:
    """Estimate 1RM using Epley formula."""
    return weight * (1 + reps / 30)


def logistic(x: float) -> float:
    """Hard-set index — returns ~1 for sets ≥80-85% intensity, ~0 for easy sets."""
    return 1.05 / (1 + math.e ** (-40 * (x - 0.75)))


def biovector_load(weight: float, reps: int, delta: float,
                   user_weight: float, rho: float, theta: float) -> float:
    """Standardised load  ψ = r·(w·Δ + m·ρ·θ)."""
    kappa = rho * theta
    return reps * (weight * delta + user_weight * kappa)


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------

class Biovector:
    """Main data-access object.  Reads JSON from the repo data/ directory."""

    def __init__(self) -> None:
        self._sets: list[dict] | None = None
        self._sessions: list[dict] | None = None
        self._exercises: list[dict] | None = None
        self._bodyweight: list[dict] | None = None
        self._exercise_index: dict[str, dict] | None = None

    # -- lazy loaders --------------------------------------------------------

    @property
    def sets(self) -> list[dict]:
        if self._sets is None:
            self._sets = _load_json(DATA_USER / "sets.json")["sets"]
        return self._sets

    @property
    def sessions(self) -> list[dict]:
        if self._sessions is None:
            self._sessions = _load_json(DATA_USER / "sessions.json")["sessions"]
        return self._sessions

    @property
    def exercises(self) -> list[dict]:
        if self._exercises is None:
            self._exercises = _load_json(DATA_REF / "exercises.json")["exercises"]
        return self._exercises

    @property
    def bodyweight(self) -> list[dict]:
        if self._bodyweight is None:
            self._bodyweight = _load_json(DATA_USER / "bodyweight.json")["measurements"]
        return self._bodyweight

    @property
    def exercise_index(self) -> dict[str, dict]:
        """Index exercises by name for quick lookup."""
        if self._exercise_index is None:
            self._exercise_index = {}
            for ex in self.exercises:
                self._exercise_index[ex["name"]] = ex
                if ex.get("short"):
                    self._exercise_index[ex["short"]] = ex
                self._exercise_index[ex["id"]] = ex
        return self._exercise_index

    # -- queries -------------------------------------------------------------

    def get_exercise(self, name_or_id: str) -> dict | None:
        """Look up an exercise by name, short code, or ID."""
        return self.exercise_index.get(name_or_id)

    def get_user_weight_at(self, timestamp: float) -> float:
        """Interpolate user bodyweight at a given timestamp."""
        bw = self.bodyweight
        if not bw:
            return 0.0
        # Binary-search style interpolation
        if timestamp <= bw[0]["timestamp"]:
            return bw[0]["weight_kg"]
        if timestamp >= bw[-1]["timestamp"]:
            return bw[-1]["weight_kg"]
        for i in range(len(bw) - 1):
            if bw[i]["timestamp"] <= timestamp <= bw[i + 1]["timestamp"]:
                t0, w0 = bw[i]["timestamp"], bw[i]["weight_kg"]
                t1, w1 = bw[i + 1]["timestamp"], bw[i + 1]["weight_kg"]
                ratio = (timestamp - t0) / (t1 - t0) if t1 != t0 else 0
                return round(w0 + ratio * (w1 - w0), 1)
        return bw[-1]["weight_kg"]

    def sets_for_exercise(self, name_or_id: str) -> list[dict]:
        """Return all sets for a given exercise."""
        ex = self.get_exercise(name_or_id)
        if not ex:
            return []
        return [s for s in self.sets if s["exercise_name"] == ex["name"]]

    def recent_sessions(self, limit: int = 5) -> list[dict]:
        """Return the N most recent sessions."""
        return sorted(self.sessions, key=lambda s: s["start_timestamp"], reverse=True)[:limit]

    def session_sets(self, session_id: str) -> list[dict]:
        """Return all sets belonging to a session (by timestamp range)."""
        session = next((s for s in self.sessions if s["id"] == session_id), None)
        if not session:
            return []
        start = session["start_timestamp"]
        end = session["end_timestamp"]
        return [s for s in self.sets if start <= s["timestamp"] <= end]

    # -- derived metrics (computed on-the-fly) --------------------------------

    def compute_set_metrics(self, set_record: dict) -> dict:
        """Compute all derived metrics for a single set."""
        ex = self.get_exercise(set_record["exercise_name"])
        w = set_record["weight"]
        r = set_record["reps"]
        ts = set_record["timestamp"]
        user_w = self.get_user_weight_at(ts)

        result: dict[str, Any] = {**set_record, "user_weight": user_w}

        result["pred_1rm"] = round(epley(w, r), 1)

        if ex:
            load = biovector_load(w, r, ex["delta"], user_w, ex["rho"], ex["theta"])
            result["load"] = round(load, 1)
            if r > 0:
                result["pred_1rl"] = round(epley(load / r, r), 1)
            else:
                result["pred_1rl"] = 0.0
        else:
            result["load"] = round(w * r, 1)
            result["pred_1rl"] = 0.0

        return result

    def exercise_1rm_history(self, name_or_id: str) -> list[dict]:
        """Return 1RM progression over time for an exercise."""
        sets = self.sets_for_exercise(name_or_id)
        history = []
        max_1rm = 0.0
        for s in sorted(sets, key=lambda x: x["timestamp"]):
            pred = round(epley(s["weight"], s["reps"]), 1)
            max_1rm = max(max_1rm, pred)
            history.append({
                "timestamp": s["timestamp"],
                "date": datetime.datetime.fromtimestamp(s["timestamp"]).strftime("%Y-%m-%d"),
                "weight": s["weight"],
                "reps": s["reps"],
                "pred_1rm": pred,
                "best_1rm": max_1rm,
            })
        return history

    # -- mutations ------------------------------------------------------------

    def add_set(self, exercise_name: str, weight: float, reps: int,
                session_name: str = "", notes: str = "") -> dict:
        """Add a new set and persist to sets.json."""
        entry: dict[str, Any] = {
            "timestamp": datetime.datetime.now().timestamp(),
            "exercise_name": exercise_name,
            "weight": weight,
            "reps": reps,
        }
        if session_name:
            entry["session_name"] = session_name
        if notes:
            entry["notes"] = notes

        self.sets.append(entry)
        _save_json(DATA_USER / "sets.json", {"sets": self.sets})
        return entry

    def list_exercises(self, category: str = "", search: str = "") -> list[dict]:
        """List exercises, optionally filtered by type category or search string."""
        results = self.exercises
        if category:
            results = [e for e in results if e.get("type", "").lower() == category.lower()]
        if search:
            search_lower = search.lower()
            results = [e for e in results
                       if search_lower in e["name"].lower()
                       or search_lower in (e.get("short") or "").lower()
                       or search_lower in e["id"].lower()]
        return results
