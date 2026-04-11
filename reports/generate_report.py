#!/usr/bin/env python3
"""Generate biovector training reports with exercise tier filtering.

Usage:
    python reports/generate_report.py --type standard
    python reports/generate_report.py --type detailed --since 2026-04-01
    python reports/generate_report.py --type full --sessions 10
    python reports/generate_report.py --type standard --output reports/latest.md

Set BIOVECTOR_DATA_DIR to override the data directory:
    BIOVECTOR_DATA_DIR=$PWD/data python reports/generate_report.py --type standard
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DATA_DIR = Path(os.environ.get("BIOVECTOR_DATA_DIR", REPO_ROOT / "data"))
DATA_USER = DATA_DIR / "user"
DATA_REF = DATA_DIR / "reference"

# ---------------------------------------------------------------------------
# Formulas (same as core.py — duplicated for standalone use)
# ---------------------------------------------------------------------------

def epley(w: float, r: float) -> float:
    return w * (1 + r / 30)

def logistic(x: float) -> float:
    return 1.05 / (1 + math.e ** (-40 * (x - 0.75)))

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)

def load_sets() -> list[dict]:
    return load_json(DATA_USER / "sets.json")["sets"]

def load_sessions() -> list[dict]:
    return load_json(DATA_USER / "sessions.json")["sessions"]

def load_exercises() -> dict[str, dict]:
    """Return exercise index keyed by name."""
    exs = load_json(DATA_REF / "exercises.json")["exercises"]
    idx: dict[str, dict] = {}
    for ex in exs:
        idx[ex["name"]] = ex
    return idx

def load_strength_states() -> dict:
    return load_json(REPO_ROOT / "strength-states.json")

def load_tiers() -> dict:
    return load_json(SCRIPT_DIR / "exercise_tiers.json")

def load_bodyweight() -> list[dict]:
    return load_json(DATA_USER / "bodyweight.json")["measurements"]

# ---------------------------------------------------------------------------
# Tier filtering
# ---------------------------------------------------------------------------

SYNONYMS = {
    "Dip": "Dips",
    "Ring Dip": "Ring Dips",
    "Bicep Curl": "Bicep Curl (Barbell)",
    "Overhead Press": "Military Press",
    "Upright Row": "Upright Row (Barbell)",
    "Hang Snatch": "Power Snatch (Barbell)",
    "Snatch": "Snatch (Barbell)",
    "Clean and Jerk": "Clean and Jerk (Barbell)",
    "Hang Clean": "Hang Clean (Barbell)",
    "Power Snatch": "Power Snatch (Barbell)",
    "Side Bend": "Side Bend (Dumbell)",
    "Reverse Military Press": "Reverse Overhead Press",
    "Unilateral Military Press": "Unilateral Overhead Press",
    "Seated Military Press (Barbell)": "Seated Overhead Press (Barbell)",
    "Hand Gripper": "Barbell Crush",
    "Supergripper": "Barbell Crush",
}

def canonical_name(name: str) -> str:
    return SYNONYMS.get(name, name)

def build_tier_sets(tiers: dict) -> tuple[set[str], set[str]]:
    """Return (tier1_names, tier2_names)."""
    t1 = {e["name"] for e in tiers["tier_1_program_lifts"]["exercises"]}
    t2: set[str] = set()
    for cat in tiers["tier_2_supporting_compounds"]["exercises_by_category"].values():
        t2.update(cat)
    return t1, t2

def classify_exercise(name: str, ex_index: dict, t1: set[str], t2: set[str]) -> int:
    """Return tier (1, 2, or 3) for an exercise name."""
    cname = canonical_name(name)
    if cname in t1:
        return 1
    if cname in t2:
        return 2
    # Check by ID prefix
    ex = ex_index.get(cname) or ex_index.get(name)
    if ex:
        prefix = ex["id"][0]
        if prefix in ("C", "G", "L", "U"):
            return 3
    return 3  # default to tier 3 if unknown

def filter_sets(sets: list[dict], report_type: str, ex_index: dict,
                t1: set[str], t2: set[str]) -> list[dict]:
    """Filter sets based on report type."""
    if report_type == "full":
        return sets
    result = []
    for s in sets:
        tier = classify_exercise(s["exercise_name"], ex_index, t1, t2)
        if report_type == "standard" and tier == 1:
            result.append(s)
        elif report_type == "detailed" and tier <= 2:
            result.append(s)
    return result

# ---------------------------------------------------------------------------
# Stats computation
# ---------------------------------------------------------------------------

def get_bw_at(timestamp: float, bw_data: list[dict]) -> float:
    if not bw_data:
        return 103.0
    if timestamp <= bw_data[0]["timestamp"]:
        return bw_data[0]["weight_kg"]
    if timestamp >= bw_data[-1]["timestamp"]:
        return bw_data[-1]["weight_kg"]
    for i in range(len(bw_data) - 1):
        if bw_data[i]["timestamp"] <= timestamp <= bw_data[i + 1]["timestamp"]:
            t0, w0 = bw_data[i]["timestamp"], bw_data[i]["weight_kg"]
            t1, w1 = bw_data[i + 1]["timestamp"], bw_data[i + 1]["weight_kg"]
            ratio = (timestamp - t0) / (t1 - t0) if t1 != t0 else 0
            return round(w0 + ratio * (w1 - w0), 1)
    return bw_data[-1]["weight_kg"]

def exercise_stats(sets: list[dict]) -> dict[str, dict]:
    """Compute per-exercise stats from a list of sets."""
    stats: dict[str, dict] = {}
    for s in sets:
        name = canonical_name(s["exercise_name"])
        if name not in stats:
            stats[name] = {
                "total_sets": 0,
                "best_weight": 0,
                "best_e1rm": 0,
                "first_ts": float("inf"),
                "last_ts": 0,
                "last_sets": [],
                "total_reps": 0,
            }
        st = stats[name]
        st["total_sets"] += 1
        st["total_reps"] += s["reps"]
        w, r = s["weight"], s["reps"]
        if w > st["best_weight"]:
            st["best_weight"] = w
        e1rm = epley(w, r) if r > 0 else w
        if e1rm > st["best_e1rm"]:
            st["best_e1rm"] = round(e1rm, 1)
        ts = s["timestamp"]
        if ts < st["first_ts"]:
            st["first_ts"] = ts
        if ts > st["last_ts"]:
            st["last_ts"] = ts
    return stats

def group_by_session(sets: list[dict]) -> list[dict]:
    """Group sets by session (date-based if no session_name)."""
    by_day: dict[str, list[dict]] = {}
    for s in sets:
        dt = datetime.fromtimestamp(s["timestamp"])
        day = dt.strftime("%Y-%m-%d")
        session_name = s.get("session_name", "")
        key = f"{day}|{session_name}" if session_name else day
        by_day.setdefault(key, []).append(s)

    sessions = []
    for key, day_sets in sorted(by_day.items(), reverse=True):
        parts = key.split("|", 1)
        date = parts[0]
        name = parts[1] if len(parts) > 1 else ""
        exercises: dict[str, list[str]] = {}
        for s in sorted(day_sets, key=lambda x: x["timestamp"]):
            ex = canonical_name(s["exercise_name"])
            exercises.setdefault(ex, []).append(f"{s['weight']}×{s['reps']}")
        sessions.append({"date": date, "name": name, "exercises": exercises})
    return sessions

def weekly_volume(sets: list[dict], ex_index: dict[str, dict],
                  bw_data: list[dict]) -> list[dict]:
    """Compute weekly standardised load."""
    weeks: dict[str, dict] = {}
    for s in sets:
        dt = datetime.fromtimestamp(s["timestamp"])
        week = dt.strftime("%G-W%V")
        if week not in weeks:
            weeks[week] = {"load": 0, "sessions": set(), "sets": 0}
        ex = ex_index.get(canonical_name(s["exercise_name"])) or ex_index.get(s["exercise_name"])
        delta = ex["delta"] if ex else 0.5
        kappa = (ex["rho"] * ex["theta"]) if ex else 0.0
        bw = get_bw_at(s["timestamp"], bw_data)
        load = s["reps"] * (s["weight"] * delta + bw * kappa)
        weeks[week]["load"] += load
        weeks[week]["sessions"].add(dt.strftime("%Y-%m-%d"))
        weeks[week]["sets"] += 1

    result = []
    for week in sorted(weeks):
        w = weeks[week]
        n_sessions = len(w["sessions"])
        result.append({
            "week": week,
            "load": round(w["load"]),
            "sessions": n_sessions,
            "avg_load": round(w["load"] / n_sessions) if n_sessions else 0,
        })
    return result

def movement_balance(sets: list[dict], ex_index: dict[str, dict],
                     bw_data: list[dict]) -> dict[str, dict]:
    """Compute load by movement category."""
    categories = {
        "Squat": {"prefixes": ["S"], "load": 0, "sets": 0},
        "Hinge": {"prefixes": ["H"], "load": 0, "sets": 0},
        "Press": {"prefixes": ["P"], "load": 0, "sets": 0},
        "Pull":  {"prefixes": ["T"], "load": 0, "sets": 0},
        "Olympic": {"prefixes": ["X"], "load": 0, "sets": 0},
    }
    for s in sets:
        cname = canonical_name(s["exercise_name"])
        ex = ex_index.get(cname) or ex_index.get(s["exercise_name"])
        if not ex:
            continue
        prefix = ex["id"][0]
        delta = ex["delta"]
        kappa = ex["rho"] * ex["theta"]
        bw = get_bw_at(s["timestamp"], bw_data)
        load = s["reps"] * (s["weight"] * delta + bw * kappa)
        for cat_name, cat in categories.items():
            if prefix in cat["prefixes"]:
                cat["load"] += load
                cat["sets"] += 1
                break
    return {k: {"load": round(v["load"]), "sets": v["sets"]}
            for k, v in categories.items()}

# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(report_type: str, since: str | None = None,
                    n_sessions: int = 10, output: str | None = None) -> str:
    """Generate a markdown report."""
    # Load data
    all_sets = load_sets()
    sessions_data = load_sessions()
    ex_index = load_exercises()
    states = load_strength_states()
    tiers = load_tiers()
    bw_data = load_bodyweight()
    t1, t2 = build_tier_sets(tiers)

    # Date filter
    if since:
        since_ts = datetime.strptime(since, "%Y-%m-%d").timestamp()
        all_sets = [s for s in all_sets if s["timestamp"] >= since_ts]

    # Tier filter
    filtered = filter_sets(all_sets, report_type, ex_index, t1, t2)

    if not filtered:
        return "# No data found for the given filters.\n"

    # Compute stats
    first_ts = min(s["timestamp"] for s in filtered)
    last_ts = max(s["timestamp"] for s in filtered)
    first_date = datetime.fromtimestamp(first_ts).strftime("%Y-%m-%d")
    last_date = datetime.fromtimestamp(last_ts).strftime("%Y-%m-%d")

    # Count unique session days
    session_days = {datetime.fromtimestamp(s["timestamp"]).strftime("%Y-%m-%d")
                    for s in filtered}

    ex_stats = exercise_stats(filtered)
    sessions = group_by_session(filtered)[:n_sessions]
    wk_vol = weekly_volume(filtered, ex_index, bw_data)

    # Tier label
    tier_label = {"standard": "Tier 1 only", "detailed": "Tier 1+2",
                  "full": "Full (all tiers)"}[report_type]

    lines: list[str] = []
    w = lines.append

    # -- Header --
    w(f"# Training Report — {report_type.title()}")
    w("")
    w(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    w(f"**Data range:** {first_date} to {last_date}")
    w(f"**Sessions in range:** {len(session_days)}")
    w(f"**Total sets (filtered):** {len(filtered)}")
    w(f"**Filter:** {tier_label}")
    w("")

    # -- Current Program State --
    w("---")
    w("")
    w("## Current Program State")
    w("")
    w(f"**Next session:** {states.get('next_session', '?')}")
    w(f"**Updated:** {states.get('updated', '?')}")
    w("")
    w("| Exercise | Load (kg) | State |")
    w("|----------|-----------|-------|")
    for abbrev, key in [("SQ", "SQ"), ("FS", "FS"), ("BP", "BP"),
                         ("DL", "DL"), ("MP", "MP"), ("PC", "PC")]:
        ex_state = states.get(key, {})
        w(f"| {abbrev} | {ex_state.get('load', '?')} | {ex_state.get('state', '?')} |")
    chins = states.get("chins_target", "?")
    dips = states.get("dips_target", "?")
    w(f"\n**Chins target:** {chins} | **Dips target:** {dips}")
    w("")

    # -- Main Lift Progression --
    w("---")
    w("")
    w("## Main Lift Progression")
    w("")
    w("| Exercise | Best Weight | Best e1RM | Total Sets | Date Range |")
    w("|----------|------------|-----------|------------|------------|")
    t1_order = ["Squat", "Front Squat", "Bench Press", "Deadlift",
                "Military Press", "Power Clean", "Chin Up", "Dips"]
    for name in t1_order:
        st = ex_stats.get(name)
        if not st:
            w(f"| {name} | — | — | 0 | — |")
            continue
        fd = datetime.fromtimestamp(st["first_ts"]).strftime("%Y-%m-%d")
        ld = datetime.fromtimestamp(st["last_ts"]).strftime("%Y-%m-%d")
        w(f"| {name} | {st['best_weight']:.0f} kg | {st['best_e1rm']:.0f} kg "
          f"| {st['total_sets']} | {fd} → {ld} |")
    w("")

    # -- Supporting exercises (detailed/full only) --
    if report_type in ("detailed", "full"):
        t2_stats = {k: v for k, v in ex_stats.items() if k not in t1}
        if t2_stats:
            w("---")
            w("")
            w("## Supporting Exercises")
            w("")
            w("| Exercise | Best Weight | Best e1RM | Sets | Reps |")
            w("|----------|------------|-----------|------|------|")
            for name, st in sorted(t2_stats.items(), key=lambda x: -x[1]["total_sets"]):
                tier = classify_exercise(name, ex_index, t1, t2)
                if tier > 2 and report_type == "detailed":
                    continue
                w(f"| {name} | {st['best_weight']:.0f} kg | {st['best_e1rm']:.0f} kg "
                  f"| {st['total_sets']} | {st['total_reps']} |")
            w("")

    # -- Recent Sessions --
    w("---")
    w("")
    w(f"## Recent Sessions (last {n_sessions})")
    w("")
    for sess in sessions:
        label = f"{sess['date']}"
        if sess["name"]:
            label += f" — {sess['name']}"
        w(f"### {label}")
        w("")
        w("| Exercise | Sets |")
        w("|----------|------|")
        for ex_name, set_strs in sess["exercises"].items():
            w(f"| {ex_name} | {', '.join(set_strs)} |")
        w("")

    # -- Volume Trends (last 12 weeks) --
    if wk_vol:
        w("---")
        w("")
        w("## Volume Trends (weekly)")
        w("")
        w("| Week | Load (ψ) | Sessions | Avg load/session |")
        w("|------|----------|----------|------------------|")
        for wk in wk_vol[-12:]:
            w(f"| {wk['week']} | {wk['load']:,} | {wk['sessions']} | {wk['avg_load']:,} |")
        w("")

    # -- Movement Balance (detailed/full) --
    if report_type in ("detailed", "full"):
        balance = movement_balance(filtered, ex_index, bw_data)
        total_load = sum(v["load"] for v in balance.values()) or 1
        w("---")
        w("")
        w("## Movement Balance")
        w("")
        w("| Category | Sets | Load (ψ) | % of total |")
        w("|----------|------|----------|------------|")
        for cat, vals in balance.items():
            pct = round(vals["load"] / total_load * 100, 1)
            w(f"| {cat} | {vals['sets']} | {vals['load']:,} | {pct}% |")
        w("")

    # -- Accessory appendix (full only) --
    if report_type == "full":
        accessory_sets = [s for s in all_sets
                          if classify_exercise(s["exercise_name"], ex_index, t1, t2) == 3]
        if accessory_sets:
            acc_stats = exercise_stats(accessory_sets)
            w("---")
            w("")
            w("## Appendix: Accessory Exercises (Tier 3)")
            w("")
            w("*⚠️ These are NOT included in the volume totals above.*")
            w("")
            w("| Exercise | Sets | Best Weight |")
            w("|----------|------|-------------|")
            for name, st in sorted(acc_stats.items(), key=lambda x: -x[1]["total_sets"]):
                w(f"| {name} | {st['total_sets']} | {st['best_weight']:.0f} kg |")
            w("")

    # -- Footer --
    w("---")
    w("")
    w("*⚠️ Accessory exercises (grip, core, arm isolation) excluded from all aggregations.*")
    w(f"*Generated by `reports/generate_report.py` on {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    report = "\n".join(lines)

    if output:
        Path(output).write_text(report)
        print(f"Report written to {output}", file=sys.stderr)

    return report

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate biovector training reports")
    parser.add_argument("--type", choices=["standard", "detailed", "full"],
                        default="standard", help="Report type (default: standard)")
    parser.add_argument("--since", type=str, default=None,
                        help="Start date filter (YYYY-MM-DD)")
    parser.add_argument("--sessions", type=int, default=10,
                        help="Number of recent sessions to show (default: 10)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output file path (default: stdout)")
    args = parser.parse_args()

    report = generate_report(
        report_type=args.type,
        since=args.since,
        n_sessions=args.sessions,
        output=args.output,
    )

    if not args.output:
        print(report)

if __name__ == "__main__":
    main()
