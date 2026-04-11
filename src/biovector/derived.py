"""Biovector derived data pipeline — generates enriched/cached data from raw sets.

This module reads all raw biovector data and produces enriched, pre-computed JSON
files in data/derived/. These files are cache artifacts — they can always be
regenerated from raw data and should be .gitignore'd.

Architecture follows data/derived/DESIGN.md:
  Pass 1: Basic enrichment (load, pred_1rm, pred_1rl, exercise metadata)
  Pass 2: Smoothed 1RM via EWRM algorithm per exercise
  Pass 3: Intensity + hardness + phi
  Pass 4: Session aggregation
  Pass 5: Per-exercise timeseries

Usage:
  python -m biovector.derived -v
  python -m biovector.derived --data-dir /path/to/data
"""

from __future__ import annotations

import argparse
import bisect
import datetime
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Reuse formulas from core
from biovector.core import epley, logistic

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PIPELINE_VERSION = "1.0.0"

# EWRM parameters (section 5.2 of DESIGN.md)
# Decay-to-floor model: strength decays toward FLOOR_RATIO of PR, not toward zero.
# This reflects physiological reality — strength persists for years.
HALF_LIFE_SECONDS = 52 * 7 * 86400  # 52 weeks (1 year) in seconds = 31_449_600
FLOOR_RATIO = 0.75  # Strength never decays below 75% of a historical PR
MIN_SESSIONS_FOR_CONFIDENCE = 3  # < 3 → "low", >= 3 → "high"

# Only exercises with >= 5 sets get a timeseries file
MIN_SETS_FOR_TIMESERIES = 5

# Fallback bodyweight if no measurements exist
DEFAULT_BW = 85.0

# Major exercises (section 7 of DESIGN.md)
MAJOR_EXERCISES: dict[str, dict[str, str]] = {
    "Squat":          {"id": "S00",    "abbrev": "SQ"},
    "Front Squat":    {"id": "S10",    "abbrev": "FS"},
    "Bench Press":    {"id": "P01.00", "abbrev": "BP"},
    "Deadlift":       {"id": "H00.0",  "abbrev": "DL"},
    "Military Press": {"id": "P10.0",  "abbrev": "MP"},
    "Power Clean":    {"id": "T20.1",  "abbrev": "PC"},
    "Chin Up":        {"id": "T00",    "abbrev": "CU"},
    "Dips":           {"id": "P20",    "abbrev": "DP"},
}

# Bodyweight exercises where weight=0 means pure BW, and weight>0 means added weight
BODYWEIGHT_EXERCISE_NAMES = {"Chin Up", "Dips", "Pull Up", "Push Up"}
# Heuristic threshold: if weight field < this, treat as added weight
BW_HEURISTIC_THRESHOLD = 50


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class DerivedDataPipeline:
    """Full derived data generation pipeline.

    Reads raw sets/sessions/bodyweight/exercises and produces:
      - enriched_sets.json          (per-set metrics)
      - sessions_enriched.json      (per-session aggregates)
      - exercise_classification.json (tier assignments)
      - exercises/<id>_<name>.json  (per-exercise timeseries)
      - metadata.json               (run metadata)
    """

    def __init__(self, data_dir: str | None = None, verbose: bool = False) -> None:
        # Resolve data directory
        if data_dir:
            self.data_dir = Path(data_dir)
        elif os.environ.get("BIOVECTOR_DATA_DIR"):
            self.data_dir = Path(os.environ["BIOVECTOR_DATA_DIR"])
        else:
            self.data_dir = Path(__file__).resolve().parent.parent.parent / "data"

        self.verbose = verbose
        self.derived_dir = self.data_dir / "derived"

        # Raw data (populated by load_data)
        self.raw_sets: list[dict] = []
        self.raw_sessions: list[dict] = []
        self.raw_bodyweight: list[dict] = []
        self.raw_exercises: list[dict] = []
        self.exercise_index: dict[str, dict] = {}  # name/id/short → exercise dict

        # Pre-built session lookup structures
        self._sorted_sessions: list[dict] = []
        self._session_starts: list[float] = []

        # Output data
        self.enriched_sets: list[dict] = []
        self.classifications: dict[str, dict] = {}
        self.enriched_sessions: list[dict] = []
        self.exercise_timeseries: dict[str, dict] = {}

    # -- logging -------------------------------------------------------------

    def log(self, msg: str) -> None:
        if self.verbose:
            print(f"  [derived] {msg}", file=sys.stderr)

    # -- data loading --------------------------------------------------------

    def load_data(self) -> None:
        """Load all raw data files from the data directory."""
        # sets.json
        with open(self.data_dir / "user" / "sets.json") as f:
            self.raw_sets = json.load(f)["sets"]
        self.log(f"Loaded {len(self.raw_sets)} sets")

        # sessions.json
        with open(self.data_dir / "user" / "sessions.json") as f:
            self.raw_sessions = json.load(f)["sessions"]
        self._build_session_index()
        self.log(f"Loaded {len(self.raw_sessions)} sessions")

        # bodyweight.json
        with open(self.data_dir / "user" / "bodyweight.json") as f:
            self.raw_bodyweight = json.load(f)["measurements"]
        self.raw_bodyweight.sort(key=lambda m: m["timestamp"])
        self.log(f"Loaded {len(self.raw_bodyweight)} bodyweight measurements")

        # exercises.json
        with open(self.data_dir / "reference" / "exercises.json") as f:
            self.raw_exercises = json.load(f)["exercises"]
        self.exercise_index = {}
        for ex in self.raw_exercises:
            self.exercise_index[ex["name"]] = ex
            if ex.get("short"):
                self.exercise_index[ex["short"]] = ex
            self.exercise_index[ex["id"]] = ex
        self.log(f"Loaded {len(self.raw_exercises)} exercise definitions")

    def _build_session_index(self) -> None:
        """Build sorted session list + start-timestamp array for bisect lookup."""
        self._sorted_sessions = sorted(
            self.raw_sessions, key=lambda s: s["start_timestamp"]
        )
        self._session_starts = [s["start_timestamp"] for s in self._sorted_sessions]

    # -- helpers -------------------------------------------------------------

    def get_bw_at(self, timestamp: float) -> float:
        """Interpolate bodyweight at a given unix timestamp."""
        bw = self.raw_bodyweight
        if not bw:
            return DEFAULT_BW
        if timestamp <= bw[0]["timestamp"]:
            return bw[0]["weight_kg"]
        if timestamp >= bw[-1]["timestamp"]:
            return bw[-1]["weight_kg"]
        # Linear interpolation between surrounding measurements
        for i in range(len(bw) - 1):
            if bw[i]["timestamp"] <= timestamp <= bw[i + 1]["timestamp"]:
                t0, w0 = bw[i]["timestamp"], bw[i]["weight_kg"]
                t1, w1 = bw[i + 1]["timestamp"], bw[i + 1]["weight_kg"]
                ratio = (timestamp - t0) / (t1 - t0) if t1 != t0 else 0.0
                return round(w0 + ratio * (w1 - w0), 1)
        return bw[-1]["weight_kg"]

    def match_session(self, timestamp: float) -> str | None:
        """Find the session ID that contains this timestamp (O(log N) via bisect)."""
        idx = bisect.bisect_right(self._session_starts, timestamp) - 1
        if idx >= 0:
            sess = self._sorted_sessions[idx]
            if sess["start_timestamp"] <= timestamp <= sess["end_timestamp"]:
                return sess["id"]
        # Check next session in case of boundary
        if idx + 1 < len(self._sorted_sessions):
            sess = self._sorted_sessions[idx + 1]
            if sess["start_timestamp"] <= timestamp <= sess["end_timestamp"]:
                return sess["id"]
        return None

    @staticmethod
    def _is_bodyweight_exercise(name: str) -> bool:
        """Check if this exercise primarily uses bodyweight as resistance."""
        return name in BODYWEIGHT_EXERCISE_NAMES

    @staticmethod
    def _effective_weight_for_1rm(weight: float, bw: float) -> float:
        """Get effective total weight for pred_1rm on bodyweight exercises.

        Heuristic from task spec:
          - weight == 0     → pure bodyweight, use bw
          - weight < 50     → added weight, use bw + weight
          - weight >= 50    → likely total weight already, use weight
        """
        if weight == 0:
            return bw
        if weight < BW_HEURISTIC_THRESHOLD:
            return bw + weight
        return weight

    # -- exercise classification (section 7) ---------------------------------

    def classify_exercises(self) -> None:
        """Classify all exercise names found in raw sets into tiers."""
        # Count sets and distinct sessions per exercise
        set_counts: dict[str, int] = defaultdict(int)
        session_names: dict[str, set] = defaultdict(set)

        for s in self.raw_sets:
            name = s["exercise_name"]
            set_counts[name] += 1
            session_names[name].add(s.get("session_name", ""))

        self.classifications = {}
        for name in set_counts:
            ex = self.exercise_index.get(name)

            # Rule 1: Hardcoded major exercises
            if name in MAJOR_EXERCISES:
                tier = "major"
            # Rule 2: Exercise exists in exercises.json
            elif ex is not None:
                ex_type = ex.get("type", "")
                ex_id = ex.get("id", "")
                first_char = ex_id[:1] if ex_id else ""

                if ex_type in ("Time", "Other") and first_char in ("C", "G", "L", "U"):
                    tier = "accessory"
                elif ex_type == "Bodyweight":
                    tier = "bodyweight"
                elif ex_type in ("Barbell", "Kettlebell"):
                    tier = "secondary"
                elif ex_type in ("Dumbell", "Dumbbell", "Machine"):
                    tier = "accessory"
                else:
                    tier = "accessory"
            # Rule 3: Not in exercises.json at all
            else:
                tier = "other"

            has_params = (
                ex is not None
                and ex.get("delta") is not None
                and ex["delta"] > 0
            )

            self.classifications[name] = {
                "id": ex["id"] if ex else None,
                "tier": tier,
                "has_params": has_params,
                "total_sets_in_data": set_counts[name],
                "total_sessions": len(session_names[name]),
            }

        self.log(f"Classified {len(self.classifications)} exercises")

    # -- Pass 1: Basic enrichment --------------------------------------------

    def pass1_basic_enrichment(self) -> None:
        """Compute per-set basic derived metrics (load, pred_1rm, pred_1rl, etc)."""
        self.log("Pass 1: Basic enrichment...")
        self.enriched_sets = []

        for s in self.raw_sets:
            ts: float = s["timestamp"]
            name: str = s["exercise_name"]
            w: float = s.get("weight", 0.0)
            r: int = s.get("reps", 0)

            ex = self.exercise_index.get(name)
            has_params = (
                ex is not None
                and ex.get("delta") is not None
                and ex["delta"] > 0
            )
            bw = self.get_bw_at(ts)
            cls = self.classifications.get(name, {})
            tier: str = cls.get("tier", "other")

            date_str = datetime.datetime.fromtimestamp(
                ts, tz=datetime.timezone.utc
            ).strftime("%Y-%m-%d")

            # Compute kappa
            kappa: float | None = None
            if ex and has_params:
                rho = ex.get("rho", 0) or 0
                theta = ex.get("theta", 0) or 0
                kappa = round(rho * theta, 4)

            enriched: dict[str, Any] = {
                # Raw fields
                "timestamp": ts,
                "exercise_name": name,
                "weight": w,
                "reps": r,
                "session_name": s.get("session_name", ""),
                "notes": s.get("notes", ""),
                # Basic derived
                "date": date_str,
                "exercise_id": ex["id"] if ex else None,
                "exercise_tier": tier,
                "has_params": has_params,
                "bw_at_time": bw,
                "delta": ex["delta"] if ex and has_params else None,
                "kappa": kappa,
            }

            # Invalid set guard: reps <= 0 or weight < 0
            if r <= 0 or w < 0:
                enriched.update({
                    "load": None, "pred_1rm": None, "pred_1rl": None,
                    "smoothed_1rm": None, "smoothed_1rl": None,
                    "smoothed_confidence": None,
                    "intensity": None, "h": None, "phi": None,
                    "is_hard_set": False,
                    "session_id": self.match_session(ts),
                })
                self.enriched_sets.append(enriched)
                continue

            # --- Load ---
            if has_params:
                delta = ex["delta"]
                kappa_val = kappa or 0.0
                load = round(r * (w * delta + bw * kappa_val), 1)
            else:
                load = round(w * r, 1)
            enriched["load"] = load

            # --- pred_1rm ---
            is_bw_ex = self._is_bodyweight_exercise(name)
            if w > 0 and r > 0:
                if is_bw_ex:
                    eff_w = self._effective_weight_for_1rm(w, bw)
                    enriched["pred_1rm"] = round(epley(eff_w, r), 1)
                else:
                    enriched["pred_1rm"] = round(epley(w, r), 1)
            elif w == 0 and is_bw_ex and r > 0:
                # Pure bodyweight exercise
                enriched["pred_1rm"] = round(epley(bw, r), 1)
            else:
                enriched["pred_1rm"] = 0.0

            # --- pred_1rl ---
            if has_params and load > 0 and r > 0:
                enriched["pred_1rl"] = round(epley(load / r, r), 1)
            else:
                enriched["pred_1rl"] = 0.0

            # Placeholders for pass 2 / pass 3
            enriched["smoothed_1rm"] = None
            enriched["smoothed_1rl"] = None
            enriched["smoothed_confidence"] = None
            enriched["intensity"] = None
            enriched["h"] = None
            enriched["phi"] = None
            enriched["is_hard_set"] = False

            # Session match
            enriched["session_id"] = self.match_session(ts)

            self.enriched_sets.append(enriched)

        self.log(f"  Enriched {len(self.enriched_sets)} sets")

    # -- Pass 2: Smoothed 1RM (EWRM) ----------------------------------------

    def pass2_smoothed_1rm(self) -> None:
        """Run the Exponentially Weighted Running Maximum algorithm per exercise.

        Uses a decay-to-floor model: strength estimates decay toward a floor
        (FLOOR_RATIO × PR) rather than toward zero. This reflects the
        physiological reality that strength persists for years even without
        training.

        For each historical set at time t_i with pred_1rm_i:
            age = current_time - t_i
            decay = 2^(-(age) / HALF_LIFE_SECONDS)
            effective_1rm = pred_1rm_i × (FLOOR_RATIO + (1 - FLOOR_RATIO) × decay)
            smoothed_1rm = max over all historical sets of effective_1rm

        With HALF_LIFE_SECONDS = 1 year and FLOOR_RATIO = 0.75:
            t=0:       100% of PR
            t=1 year:  87.5% of PR
            t=2 years: 81.25% of PR
            t=3 years: 78.1% of PR
            t→∞:       75% of PR (floor)
        """
        self.log("Pass 2: Smoothed 1RM (EWRM, decay-to-floor)...")

        # Group enriched set indices by exercise name
        exercise_indices: dict[str, list[int]] = defaultdict(list)
        for i, s in enumerate(self.enriched_sets):
            exercise_indices[s["exercise_name"]].append(i)

        ceiling = 1 - FLOOR_RATIO  # portion that decays (0.25)

        for ex_name, indices in exercise_indices.items():
            # Ensure chronological order
            indices.sort(key=lambda i: self.enriched_sets[i]["timestamp"])

            # Collect all (timestamp, pred_1rm/pred_1rl) tuples as history
            history_1rm: list[tuple[float, float]] = []
            history_1rl: list[tuple[float, float]] = []
            session_count = 0
            last_session_id: str | None = None

            for idx in indices:
                s = self.enriched_sets[idx]
                ts = s["timestamp"]

                # Skip sets with no valid pred_1rm
                if s["pred_1rm"] is None:
                    continue

                pred_1rm: float = s["pred_1rm"]
                pred_1rl: float = s["pred_1rl"] or 0.0

                # Add current set to history
                if pred_1rm > 0:
                    history_1rm.append((ts, pred_1rm))
                if pred_1rl > 0:
                    history_1rl.append((ts, pred_1rl))

                # Compute smoothed_1rm as max of all historical effective values
                smoothed_1rm = 0.0
                for t_i, pr_i in history_1rm:
                    age = ts - t_i
                    decay = 2 ** (-(age) / HALF_LIFE_SECONDS)
                    effective = pr_i * (FLOOR_RATIO + ceiling * decay)
                    if effective > smoothed_1rm:
                        smoothed_1rm = effective

                smoothed_1rl = 0.0
                for t_i, pr_i in history_1rl:
                    age = ts - t_i
                    decay = 2 ** (-(age) / HALF_LIFE_SECONDS)
                    effective = pr_i * (FLOOR_RATIO + ceiling * decay)
                    if effective > smoothed_1rl:
                        smoothed_1rl = effective

                # Track distinct sessions
                current_session = (
                    s["session_id"] or s["session_name"] or f"ts_{ts}"
                )
                if current_session != last_session_id:
                    session_count += 1
                    last_session_id = current_session

                # Confidence (DESIGN.md section 5.2)
                if session_count < MIN_SESSIONS_FOR_CONFIDENCE:
                    confidence = "low"
                else:
                    confidence = "high"

                # Write back
                self.enriched_sets[idx]["smoothed_1rm"] = round(smoothed_1rm, 1)
                self.enriched_sets[idx]["smoothed_1rl"] = round(smoothed_1rl, 1)
                self.enriched_sets[idx]["smoothed_confidence"] = confidence

        self.log("  EWRM complete")

    # -- Pass 3: Intensity + hardness ----------------------------------------

    def pass3_intensity(self) -> None:
        """Compute intensity, h, phi, is_hard_set from smoothed values."""
        self.log("Pass 3: Intensity + hardness...")

        for s in self.enriched_sets:
            smoothed_1rl = s.get("smoothed_1rl") or 0.0
            pred_1rl = s.get("pred_1rl") or 0.0
            load = s.get("load") or 0.0
            confidence = s.get("smoothed_confidence")

            if smoothed_1rl > 0 and pred_1rl > 0 and confidence is not None:
                intensity = round(pred_1rl / smoothed_1rl, 4)
                h = round(logistic(intensity), 4)
                phi = round(load * h, 1)

                s["intensity"] = intensity
                s["h"] = h
                s["phi"] = phi
                s["is_hard_set"] = h >= 0.5
            # else: keep null defaults from pass 1

        self.log("  Intensity computation complete")

    # -- Pass 4: Session aggregation -----------------------------------------

    def pass4_session_aggregation(self) -> None:
        """Aggregate enriched sets into per-session summaries."""
        self.log("Pass 4: Session aggregation...")

        # Group sets by session_id
        session_sets: dict[str, list[dict]] = defaultdict(list)
        for s in self.enriched_sets:
            sid = s.get("session_id")
            if sid:
                session_sets[sid].append(s)

        self.enriched_sessions = []
        for sess in self.raw_sessions:
            sid = sess["id"]
            sets = session_sets.get(sid, [])
            if not sets:
                continue

            bw = sets[0]["bw_at_time"]
            date_str = datetime.datetime.fromtimestamp(
                sess["start_timestamp"], tz=datetime.timezone.utc
            ).strftime("%Y-%m-%d")
            duration = round(
                (sess["end_timestamp"] - sess["start_timestamp"]) / 60
            )

            # Per-exercise aggregation
            ex_groups: dict[str, list[dict]] = defaultdict(list)
            for st in sets:
                ex_groups[st["exercise_name"]].append(st)

            per_exercise: dict[str, dict] = {}
            for ex_name, ex_sets in ex_groups.items():
                total_reps = sum(st["reps"] for st in ex_sets if st["reps"])
                total_load = sum(st.get("load") or 0 for st in ex_sets)
                total_phi = sum(st.get("phi") or 0 for st in ex_sets)
                pred_1rms = [
                    st["pred_1rm"] for st in ex_sets
                    if st.get("pred_1rm") and st["pred_1rm"] > 0
                ]
                h_values = [
                    st["h"] for st in ex_sets if st.get("h") is not None
                ]
                intensities = [
                    st["intensity"] for st in ex_sets
                    if st.get("intensity") is not None
                ]

                per_exercise[ex_name] = {
                    "sets": len(ex_sets),
                    "total_reps": total_reps,
                    "total_load": round(total_load, 1),
                    "total_phi": round(total_phi, 1),
                    "best_pred_1rm": (
                        round(max(pred_1rms), 1) if pred_1rms else 0.0
                    ),
                    "hard_sets": (
                        round(sum(h_values), 1) if h_values else 0.0
                    ),
                    "avg_intensity": (
                        round(sum(intensities) / len(intensities), 4)
                        if intensities else None
                    ),
                }

            # Session totals
            all_h = [st["h"] for st in sets if st.get("h") is not None]
            major_h = [
                st["h"] for st in sets
                if st.get("h") is not None
                and st["exercise_tier"] in ("major", "secondary")
            ]

            total_load = sum(st.get("load") or 0 for st in sets)
            total_phi_val = sum(st.get("phi") or 0 for st in sets)
            total_hard_sets = sum(all_h) if all_h else 0.0

            # Volume indices: Ψ * bw^(-2/3) and Φ * bw^(-2/3)
            bw_factor = bw ** (2 / 3) if bw > 0 else 1.0

            # Intensity distribution (DESIGN.md section 4)
            warmup = moderate = hard = near_max = 0
            for st in sets:
                h_val = st.get("h")
                if h_val is None or h_val < 0.1:
                    warmup += 1
                elif h_val < 0.5:
                    moderate += 1
                elif h_val < 1.02:
                    hard += 1
                else:
                    near_max += 1

            enriched_sess: dict[str, Any] = {
                "id": sid,
                "name": sess.get("name", ""),
                "date": date_str,
                "start_timestamp": sess["start_timestamp"],
                "end_timestamp": sess["end_timestamp"],
                "duration_minutes": duration,
                "bw_at_time": bw,
                "total_sets": len(sets),
                "exercise_count": len(ex_groups),
                "exercises_performed": list(ex_groups.keys()),
                "per_exercise": per_exercise,
                "totals": {
                    "total_load": round(total_load, 1),
                    "total_hard_load": round(total_phi_val, 1),
                    "total_hard_sets": round(total_hard_sets, 1),
                    "total_hard_sets_major": (
                        round(sum(major_h), 1) if major_h else 0.0
                    ),
                    "volume_index": round(total_load / bw_factor, 1),
                    "hard_volume_index": round(total_phi_val / bw_factor, 1),
                },
                "intensity_distribution": {
                    "warmup_sets": warmup,
                    "moderate_sets": moderate,
                    "hard_sets": hard,
                    "near_max_sets": near_max,
                },
            }
            self.enriched_sessions.append(enriched_sess)

        self.enriched_sessions.sort(key=lambda s: s["start_timestamp"])
        self.log(f"  Aggregated {len(self.enriched_sessions)} sessions")

    # -- Pass 5: Per-exercise timeseries -------------------------------------

    def pass5_exercise_timeseries(self) -> None:
        """Build per-exercise timeseries (one per session, one file per exercise)."""
        self.log("Pass 5: Exercise timeseries...")

        # Group enriched sets by exercise name
        exercise_sets: dict[str, list[dict]] = defaultdict(list)
        for s in self.enriched_sets:
            exercise_sets[s["exercise_name"]].append(s)

        self.exercise_timeseries = {}
        for ex_name, sets in exercise_sets.items():
            if len(sets) < MIN_SETS_FOR_TIMESERIES:
                continue

            sets.sort(key=lambda s: s["timestamp"])

            ex = self.exercise_index.get(ex_name)
            has_params = (
                ex is not None
                and ex.get("delta") is not None
                and ex["delta"] > 0
            )
            cls = self.classifications.get(ex_name, {})

            # Group by session_id (or date fallback for unmatched sets)
            session_groups: dict[str, list[dict]] = defaultdict(list)
            for s in sets:
                sid = s.get("session_id") or f"nosess_{s['date']}"
                session_groups[sid].append(s)

            session_series: list[dict] = []
            for sid, sess_sets in session_groups.items():
                sess_sets.sort(key=lambda x: x["timestamp"])

                date_str = sess_sets[0]["date"]
                weights = [s["weight"] for s in sess_sets if s["weight"] > 0]
                best_weight = max(weights) if weights else 0.0

                # Find reps at best weight
                reps_at_best = 0
                for s in sess_sets:
                    if s["weight"] == best_weight and s["reps"] > reps_at_best:
                        reps_at_best = s["reps"]

                pred_1rms = [
                    s["pred_1rm"] for s in sess_sets
                    if s.get("pred_1rm") and s["pred_1rm"] > 0
                ]
                loads = [s.get("load") or 0 for s in sess_sets]
                phis = [s.get("phi") or 0 for s in sess_sets]
                h_vals = [s["h"] for s in sess_sets if s.get("h") is not None]
                intensities = [
                    s["intensity"] for s in sess_sets
                    if s.get("intensity") is not None
                ]

                # Smoothed values: take last set's (most recent after EWRM)
                last_1rm = sess_sets[-1].get("smoothed_1rm") or 0.0
                last_1rl = sess_sets[-1].get("smoothed_1rl") or 0.0

                session_series.append({
                    "date": date_str,
                    "session_id": sid,
                    "sets": len(sess_sets),
                    "best_weight": best_weight,
                    "best_reps_at_best_weight": reps_at_best,
                    "best_pred_1rm": (
                        round(max(pred_1rms), 1) if pred_1rms else 0.0
                    ),
                    "smoothed_1rm": round(last_1rm, 1),
                    "smoothed_1rl": round(last_1rl, 1),
                    "total_load": round(sum(loads), 1),
                    "total_phi": round(sum(phis), 1),
                    "hard_sets": (
                        round(sum(h_vals), 1) if h_vals else 0.0
                    ),
                    "avg_intensity": (
                        round(sum(intensities) / len(intensities), 4)
                        if intensities else None
                    ),
                })

            session_series.sort(key=lambda x: x["date"])

            # Overall exercise stats
            all_pred_1rms = [
                s["pred_1rm"] for s in sets
                if s.get("pred_1rm") and s["pred_1rm"] > 0
            ]
            date_first = session_series[0]["date"] if session_series else ""
            date_last = session_series[-1]["date"] if session_series else ""
            current_1rm = (
                session_series[-1]["smoothed_1rm"] if session_series else 0.0
            )
            current_1rl = (
                session_series[-1]["smoothed_1rl"] if session_series else 0.0
            )

            self.exercise_timeseries[ex_name] = {
                "exercise_name": ex_name,
                "exercise_id": ex["id"] if ex else None,
                "exercise_tier": cls.get("tier", "other"),
                "has_params": has_params,
                "total_sets": len(sets),
                "total_sessions": len(session_series),
                "date_range": {"first": date_first, "last": date_last},
                "current_smoothed_1rm": round(current_1rm, 1),
                "current_smoothed_1rl": round(current_1rl, 1),
                "all_time_best_pred_1rm": (
                    round(max(all_pred_1rms), 1) if all_pred_1rms else 0.0
                ),
                "session_series": session_series,
            }

        self.log(
            f"  Built timeseries for {len(self.exercise_timeseries)} exercises"
        )

    # -- Output writing ------------------------------------------------------

    def write_output(self) -> None:
        """Write all derived data files to data/derived/."""
        self.log("Writing output files...")

        self.derived_dir.mkdir(parents=True, exist_ok=True)
        exercises_dir = self.derived_dir / "exercises"
        exercises_dir.mkdir(parents=True, exist_ok=True)

        now_str = datetime.datetime.now(
            tz=datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        # --- enriched_sets.json ---
        with open(self.derived_dir / "enriched_sets.json", "w") as f:
            json.dump(
                {
                    "version": PIPELINE_VERSION,
                    "generated_at": now_str,
                    "sets": self.enriched_sets,
                },
                f,
                indent=2,
            )
        self.log(f"  Wrote enriched_sets.json ({len(self.enriched_sets)} sets)")

        # --- sessions_enriched.json ---
        with open(self.derived_dir / "sessions_enriched.json", "w") as f:
            json.dump(
                {
                    "version": PIPELINE_VERSION,
                    "generated_at": now_str,
                    "sessions": self.enriched_sessions,
                },
                f,
                indent=2,
            )
        self.log(
            f"  Wrote sessions_enriched.json "
            f"({len(self.enriched_sessions)} sessions)"
        )

        # --- exercise_classification.json ---
        with open(self.derived_dir / "exercise_classification.json", "w") as f:
            json.dump(
                {
                    "version": PIPELINE_VERSION,
                    "generated_at": now_str,
                    "classifications": self.classifications,
                },
                f,
                indent=2,
            )
        self.log("  Wrote exercise_classification.json")

        # --- Per-exercise timeseries files ---
        ts_count = 0
        for ex_name, ts_data in self.exercise_timeseries.items():
            ex_id = ts_data["exercise_id"] or "unknown"
            snake_name = (
                ex_name.lower()
                .replace(" ", "_")
                .replace("-", "_")
                .replace("(", "")
                .replace(")", "")
            )
            filename = f"{ex_id}_{snake_name}.json"

            with open(exercises_dir / filename, "w") as f:
                json.dump(ts_data, f, indent=2)
            ts_count += 1
        self.log(f"  Wrote {ts_count} exercise timeseries files")

        # --- metadata.json ---
        last_ts = (
            max(s["timestamp"] for s in self.raw_sets) if self.raw_sets else 0
        )
        with open(self.derived_dir / "metadata.json", "w") as f:
            json.dump(
                {
                    "generated_at": now_str,
                    "pipeline_version": PIPELINE_VERSION,
                    "total_sets_processed": len(self.enriched_sets),
                    "total_sessions": len(self.enriched_sessions),
                    "total_exercises": len(self.classifications),
                    "exercises_with_timeseries": ts_count,
                    "last_raw_set_timestamp": last_ts,
                    "smoothing_half_life_weeks": 52,
                    "smoothing_floor_ratio": FLOOR_RATIO,
                    "min_sessions_for_confidence": MIN_SESSIONS_FOR_CONFIDENCE,
                },
                f,
                indent=2,
            )
        self.log("  Wrote metadata.json")

    # -- Main pipeline entry point -------------------------------------------

    def run(self) -> None:
        """Execute the full derived data pipeline."""
        print(f"Biovector Derived Data Pipeline v{PIPELINE_VERSION}")
        print(f"Data directory: {self.data_dir}")
        print()

        self.load_data()
        self.classify_exercises()
        self.pass1_basic_enrichment()
        self.pass2_smoothed_1rm()
        self.pass3_intensity()
        self.pass4_session_aggregation()
        self.pass5_exercise_timeseries()
        self.write_output()

        print()
        print(
            f"Pipeline complete: "
            f"{len(self.enriched_sets)} sets, "
            f"{len(self.enriched_sessions)} sessions, "
            f"{len(self.exercise_timeseries)} exercise timeseries"
        )
        print(f"Output: {self.derived_dir}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point for derived data generation."""
    parser = argparse.ArgumentParser(
        description="Generate derived data from raw training sets"
    )
    parser.add_argument("--data-dir", help="Override data directory")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print detailed progress")
    args = parser.parse_args()

    pipeline = DerivedDataPipeline(
        data_dir=args.data_dir, verbose=args.verbose
    )
    pipeline.run()


if __name__ == "__main__":
    main()
