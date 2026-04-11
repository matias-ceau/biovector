#!/usr/bin/env python3
"""Generate biovector training reports with charts and exercise tier filtering.

Usage:
    python reports/generate_report.py --type standard
    python reports/generate_report.py --type detailed --since 2026-04-01
    python reports/generate_report.py --type full --sessions 10
    python reports/generate_report.py --type standard -o reports/latest.md

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
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

COLORS = {
    "Squat":        "#e74c3c",
    "Front Squat":  "#c0392b",
    "Bench Press":  "#3498db",
    "Deadlift":     "#2ecc71",
    "Military Press":"#f39c12",
    "Power Clean":  "#9b59b6",
    "Chin Up":      "#1abc9c",
    "Dips":         "#e67e22",
}
CAT_COLORS = {
    "Squat":   "#e74c3c",
    "Hinge":   "#2ecc71",
    "Press":   "#3498db",
    "Pull":    "#9b59b6",
    "Olympic": "#f39c12",
}
BG_COLOR  = "#1e1e2e"
FG_COLOR  = "#cdd6f4"
GRID_COLOR = "#45475a"
ACCENT     = "#89b4fa"

def apply_style():
    plt.rcParams.update({
        "figure.facecolor":   BG_COLOR,
        "axes.facecolor":     BG_COLOR,
        "axes.edgecolor":     GRID_COLOR,
        "axes.labelcolor":    FG_COLOR,
        "text.color":         FG_COLOR,
        "xtick.color":        FG_COLOR,
        "ytick.color":        FG_COLOR,
        "grid.color":         GRID_COLOR,
        "grid.alpha":         0.3,
        "legend.facecolor":   "#313244",
        "legend.edgecolor":   GRID_COLOR,
        "legend.labelcolor":  FG_COLOR,
        "figure.dpi":         150,
        "savefig.dpi":        150,
        "savefig.bbox":       "tight",
        "savefig.pad_inches": 0.2,
        "font.family":        "sans-serif",
        "font.size":          10,
    })

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DATA_DIR = Path(os.environ.get("BIOVECTOR_DATA_DIR", REPO_ROOT / "data"))
DATA_USER = DATA_DIR / "user"
DATA_REF = DATA_DIR / "reference"

# ---------------------------------------------------------------------------
# Formulas
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
    "Dip": "Dips", "Ring Dip": "Ring Dips",
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
    "Hand Gripper": "Barbell Crush", "Supergripper": "Barbell Crush",
}

def canonical_name(name: str) -> str:
    return SYNONYMS.get(name, name)

def build_tier_sets(tiers: dict) -> tuple[set[str], set[str]]:
    t1 = {e["name"] for e in tiers["tier_1_program_lifts"]["exercises"]}
    t2: set[str] = set()
    for cat in tiers["tier_2_supporting_compounds"]["exercises_by_category"].values():
        t2.update(cat)
    return t1, t2

def classify_exercise(name: str, ex_index: dict, t1: set[str], t2: set[str]) -> int:
    cname = canonical_name(name)
    if cname in t1:
        return 1
    if cname in t2:
        return 2
    ex = ex_index.get(cname) or ex_index.get(name)
    if ex:
        prefix = ex["id"][0]
        if prefix in ("C", "G", "L", "U"):
            return 3
    return 3

def filter_sets(sets: list[dict], report_type: str, ex_index: dict,
                t1: set[str], t2: set[str]) -> list[dict]:
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
# Stats
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
    stats: dict[str, dict] = {}
    for s in sets:
        name = canonical_name(s["exercise_name"])
        if name not in stats:
            stats[name] = {
                "total_sets": 0, "best_weight": 0, "best_e1rm": 0,
                "first_ts": float("inf"), "last_ts": 0,
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
    weeks: dict[str, dict] = {}
    for s in sets:
        dt = datetime.fromtimestamp(s["timestamp"])
        week = dt.strftime("%G-W%V")
        if week not in weeks:
            weeks[week] = {"load": 0, "sessions": set(), "sets": 0,
                           "first_day": dt}
        ex = ex_index.get(canonical_name(s["exercise_name"])) or ex_index.get(s["exercise_name"])
        delta = ex["delta"] if ex else 0.5
        kappa = (ex["rho"] * ex["theta"]) if ex else 0.0
        bw = get_bw_at(s["timestamp"], bw_data)
        load = s["reps"] * (s["weight"] * delta + bw * kappa)
        weeks[week]["load"] += load
        weeks[week]["sessions"].add(dt.strftime("%Y-%m-%d"))
        weeks[week]["sets"] += 1
        if dt < weeks[week]["first_day"]:
            weeks[week]["first_day"] = dt

    result = []
    for week in sorted(weeks):
        w = weeks[week]
        n_sessions = len(w["sessions"])
        result.append({
            "week": week,
            "load": round(w["load"]),
            "sessions": n_sessions,
            "avg_load": round(w["load"] / n_sessions) if n_sessions else 0,
            "date": w["first_day"],
        })
    return result

def movement_balance(sets: list[dict], ex_index: dict[str, dict],
                     bw_data: list[dict]) -> dict[str, dict]:
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
# Chart generation
# ---------------------------------------------------------------------------

def chart_main_lift_progression(sets: list[dict], out_dir: Path) -> str:
    """Generate 1RM progression chart for main lifts. Returns filename."""
    apply_style()
    fig, ax = plt.subplots(figsize=(12, 6))

    t1_lifts = ["Squat", "Front Squat", "Bench Press", "Deadlift",
                "Military Press", "Power Clean"]

    for lift in t1_lifts:
        lift_sets = sorted(
            [s for s in sets if canonical_name(s["exercise_name"]) == lift
             and s["weight"] > 0],
            key=lambda x: x["timestamp"],
        )
        if not lift_sets:
            continue

        # Compute rolling best e1RM
        dates, best_e1rms = [], []
        running_max = 0.0
        for s in lift_sets:
            e1rm = epley(s["weight"], s["reps"])
            running_max = max(running_max, e1rm)
            dates.append(datetime.fromtimestamp(s["timestamp"]))
            best_e1rms.append(running_max)

        color = COLORS.get(lift, ACCENT)
        ax.plot(dates, best_e1rms, label=lift, color=color, linewidth=2, alpha=0.9)
        # Mark latest point
        ax.scatter([dates[-1]], [best_e1rms[-1]], color=color, s=40, zorder=5)
        ax.annotate(f"{best_e1rms[-1]:.0f}",
                    xy=(dates[-1], best_e1rms[-1]),
                    xytext=(6, 0), textcoords="offset points",
                    fontsize=8, color=color, fontweight="bold")

    ax.set_title("Main Lift e1RM Progression", fontsize=14, fontweight="bold", pad=12)
    ax.set_ylabel("Estimated 1RM (kg)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", framealpha=0.9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate(rotation=30)

    fname = "chart_main_lifts.png"
    fig.savefig(out_dir / fname)
    plt.close(fig)
    return fname


def chart_volume_trends(wk_vol: list[dict], out_dir: Path) -> str:
    """Generate weekly volume bar chart. Returns filename."""
    apply_style()
    fig, ax1 = plt.subplots(figsize=(12, 5))

    dates = [w["date"] for w in wk_vol]
    loads = [w["load"] for w in wk_vol]
    sessions = [w["sessions"] for w in wk_vol]

    # Volume bars
    bars = ax1.bar(dates, loads, width=5, color=ACCENT, alpha=0.7, label="Weekly Load (ψ)")
    ax1.set_ylabel("Standardised Load (ψ) kg·m")
    ax1.set_title("Weekly Training Volume", fontsize=14, fontweight="bold", pad=12)
    ax1.grid(True, axis="y", alpha=0.3)

    # Session count overlay
    ax2 = ax1.twinx()
    ax2.plot(dates, sessions, color="#f38ba8", marker="o", markersize=4,
             linewidth=1.5, label="Sessions", alpha=0.8)
    ax2.set_ylabel("Sessions / week", color="#f38ba8")
    ax2.tick_params(axis="y", labelcolor="#f38ba8")
    ax2.yaxis.set_major_locator(MaxNLocator(integer=True))

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", framealpha=0.9)

    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate(rotation=30)

    fname = "chart_volume.png"
    fig.savefig(out_dir / fname)
    plt.close(fig)
    return fname


def chart_movement_balance(balance: dict[str, dict], out_dir: Path) -> str:
    """Generate movement balance donut chart. Returns filename."""
    apply_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

    cats = list(balance.keys())
    loads = [balance[c]["load"] for c in cats]
    sets_count = [balance[c]["sets"] for c in cats]
    colors = [CAT_COLORS.get(c, ACCENT) for c in cats]

    # Donut — by load
    wedges, texts, autotexts = ax1.pie(
        loads, labels=cats, colors=colors, autopct="%1.0f%%",
        startangle=90, pctdistance=0.75,
        wedgeprops={"width": 0.4, "edgecolor": BG_COLOR, "linewidth": 2},
    )
    for t in autotexts:
        t.set_fontsize(9)
        t.set_color(FG_COLOR)
    ax1.set_title("By Load (ψ)", fontsize=12, fontweight="bold")

    # Donut — by sets
    wedges2, texts2, autotexts2 = ax2.pie(
        sets_count, labels=cats, colors=colors, autopct="%1.0f%%",
        startangle=90, pctdistance=0.75,
        wedgeprops={"width": 0.4, "edgecolor": BG_COLOR, "linewidth": 2},
    )
    for t in autotexts2:
        t.set_fontsize(9)
        t.set_color(FG_COLOR)
    ax2.set_title("By Sets", fontsize=12, fontweight="bold")

    fig.suptitle("Movement Balance", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()

    fname = "chart_balance.png"
    fig.savefig(out_dir / fname)
    plt.close(fig)
    return fname


def chart_recent_sessions(sessions: list[dict], ex_index: dict, bw_data: list[dict],
                          out_dir: Path) -> str:
    """Generate per-session load stacked bar chart. Returns filename."""
    apply_style()

    # Reverse so chronological order is left-to-right
    sessions = list(reversed(sessions))
    if len(sessions) > 15:
        sessions = sessions[-15:]

    # Compute session loads per category
    cat_prefixes = {"Squat": "S", "Hinge": "H", "Press": "P", "Pull": "T", "Olympic": "X"}
    session_data: list[dict] = []
    for sess in sessions:
        cat_loads: dict[str, float] = {c: 0 for c in cat_prefixes}
        for ex_name, set_strs in sess["exercises"].items():
            cname = canonical_name(ex_name)
            ex = ex_index.get(cname) or ex_index.get(ex_name)
            if not ex:
                continue
            prefix = ex["id"][0]
            delta = ex["delta"]
            kappa = ex["rho"] * ex["theta"]
            bw = 103.0  # approximate for chart
            for ss in set_strs:
                try:
                    w_str, r_str = ss.split("×")
                    w, r = float(w_str), float(r_str)
                    load = r * (w * delta + bw * kappa)
                except ValueError:
                    load = 0
                for cat, pfx in cat_prefixes.items():
                    if prefix == pfx:
                        cat_loads[cat] += load
                        break
        session_data.append({
            "label": sess["date"].split("-", 1)[1],  # MM-DD
            "name": sess.get("name", ""),
            **{c: round(v) for c, v in cat_loads.items()},
        })

    fig, ax = plt.subplots(figsize=(12, 5))
    labels = [d["label"] + (f"\n{d['name']}" if d["name"] else "") for d in session_data]
    x = range(len(labels))
    bottom = [0.0] * len(session_data)

    for cat in cat_prefixes:
        vals = [d[cat] for d in session_data]
        color = CAT_COLORS.get(cat, ACCENT)
        ax.bar(x, vals, bottom=bottom, label=cat, color=color, alpha=0.85, width=0.7)
        bottom = [b + v for b, v in zip(bottom, vals)]

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=7, rotation=45, ha="right")
    ax.set_ylabel("Session Load (ψ) kg·m")
    ax.set_title("Per-Session Load Breakdown", fontsize=14, fontweight="bold", pad=12)
    ax.legend(loc="upper left", framealpha=0.9, fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()

    fname = "chart_sessions.png"
    fig.savefig(out_dir / fname)
    plt.close(fig)
    return fname


def chart_bodyweight_chinup_dip(sets: list[dict], out_dir: Path) -> str:
    """Chart bodyweight exercise rep totals per session."""
    apply_style()
    fig, ax = plt.subplots(figsize=(10, 4))

    for ex_name, color, marker in [("Chin Up", "#1abc9c", "o"), ("Dips", "#e67e22", "s")]:
        ex_sets = sorted(
            [s for s in sets if canonical_name(s["exercise_name"]) == ex_name],
            key=lambda x: x["timestamp"],
        )
        if not ex_sets:
            continue

        # Group by day
        daily: dict[str, int] = {}
        for s in ex_sets:
            day = datetime.fromtimestamp(s["timestamp"]).strftime("%Y-%m-%d")
            daily[day] = daily.get(day, 0) + s["reps"]

        dates = [datetime.strptime(d, "%Y-%m-%d") for d in sorted(daily)]
        reps = [daily[d.strftime("%Y-%m-%d")] for d in dates]
        ax.plot(dates, reps, label=ex_name, color=color, marker=marker,
                markersize=5, linewidth=1.5, alpha=0.8)

    ax.set_title("Bodyweight Exercise — Total Reps per Session",
                 fontsize=13, fontweight="bold", pad=10)
    ax.set_ylabel("Total Reps")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate(rotation=30)

    fname = "chart_bw_exercises.png"
    fig.savefig(out_dir / fname)
    plt.close(fig)
    return fname

# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(report_type: str, since: str | None = None,
                    n_sessions: int = 10, output: str | None = None) -> str:
    """Generate a markdown report with embedded charts."""
    # Determine output directory for charts
    if output:
        out_dir = Path(output).parent
    else:
        out_dir = SCRIPT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    all_sets = load_sets()
    ex_index = load_exercises()
    states = load_strength_states()
    tiers = load_tiers()
    bw_data = load_bodyweight()
    t1, t2 = build_tier_sets(tiers)

    # Date filter
    if since:
        since_ts = datetime.strptime(since, "%Y-%m-%d").timestamp()
        all_sets = [s for s in all_sets if s["timestamp"] >= since_ts]

    # Tier filter for tables/stats
    filtered = filter_sets(all_sets, report_type, ex_index, t1, t2)
    if not filtered:
        return "# No data found for the given filters.\n"

    # Compute stats
    first_ts = min(s["timestamp"] for s in filtered)
    last_ts = max(s["timestamp"] for s in filtered)
    first_date = datetime.fromtimestamp(first_ts).strftime("%Y-%m-%d")
    last_date = datetime.fromtimestamp(last_ts).strftime("%Y-%m-%d")
    session_days = {datetime.fromtimestamp(s["timestamp"]).strftime("%Y-%m-%d")
                    for s in filtered}

    ex_stats = exercise_stats(filtered)
    sessions = group_by_session(filtered)
    wk_vol = weekly_volume(filtered, ex_index, bw_data)
    balance = movement_balance(filtered, ex_index, bw_data)

    tier_label = {"standard": "Tier 1 only", "detailed": "Tier 1+2",
                  "full": "Full (all tiers)"}[report_type]

    # --- Generate charts ---
    print("Generating charts...", file=sys.stderr)
    chart_files: dict[str, str] = {}

    chart_files["lifts"] = chart_main_lift_progression(filtered, out_dir)
    if wk_vol:
        chart_files["volume"] = chart_volume_trends(wk_vol, out_dir)
    if any(v["load"] > 0 for v in balance.values()):
        chart_files["balance"] = chart_movement_balance(balance, out_dir)
    chart_files["sessions"] = chart_recent_sessions(
        sessions[:n_sessions], ex_index, bw_data, out_dir
    )
    chart_files["bw"] = chart_bodyweight_chinup_dip(filtered, out_dir)

    print(f"Charts saved to {out_dir}/", file=sys.stderr)

    # --- Build markdown ---
    lines: list[str] = []
    w = lines.append

    # Header
    w(f"# 🏋️ Training Report — {report_type.title()}")
    w("")
    w(f"> **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ")
    w(f"> **Data range:** {first_date} → {last_date}  ")
    w(f"> **Sessions:** {len(session_days)} · **Sets:** {len(filtered)} · **Filter:** {tier_label}")
    w("")

    # Current Program State
    w("---")
    w("")
    w("## 📋 Current Program State")
    w("")
    w(f"**Next session:** `{states.get('next_session', '?')}`  ")
    w(f"**Last updated:** {states.get('updated', '?')}")
    w("")
    w("| Exercise | Load | State | | Exercise | Load | State |")
    w("|----------|------|-------|-|----------|------|-------|")
    state_rows = [("SQ", "SQ"), ("FS", "FS"), ("BP", "BP"),
                  ("DL", "DL"), ("MP", "MP"), ("PC", "PC")]
    for i in range(0, len(state_rows), 2):
        a1, k1 = state_rows[i]
        s1 = states.get(k1, {})
        a2, k2 = state_rows[i + 1]
        s2 = states.get(k2, {})
        w(f"| **{a1}** | {s1.get('load', '?')} kg | `{s1.get('state', '?')}` |"
          f" | **{a2}** | {s2.get('load', '?')} kg | `{s2.get('state', '?')}` |")
    w("")
    w(f"🎯 **Chins target:** {states.get('chins_target', '?')} · "
      f"**Dips target:** {states.get('dips_target', '?')}")
    w("")

    # Main Lift Progression chart
    w("---")
    w("")
    w("## 📈 Main Lift Progression")
    w("")
    if "lifts" in chart_files:
        w(f"![Main Lift e1RM Progression]({chart_files['lifts']})")
        w("")

    w("| Exercise | Best Weight | Best e1RM | Sets | Period |")
    w("|:---------|:----------:|:---------:|:----:|:------:|")
    t1_order = ["Squat", "Front Squat", "Bench Press", "Deadlift",
                "Military Press", "Power Clean", "Chin Up", "Dips"]
    for name in t1_order:
        st = ex_stats.get(name)
        if not st:
            w(f"| {name} | — | — | 0 | — |")
            continue
        fd = datetime.fromtimestamp(st["first_ts"]).strftime("%Y-%m-%d")
        ld = datetime.fromtimestamp(st["last_ts"]).strftime("%Y-%m-%d")
        w(f"| **{name}** | {st['best_weight']:.0f} kg | {st['best_e1rm']:.0f} kg "
          f"| {st['total_sets']} | {fd} → {ld} |")
    w("")

    # Bodyweight exercises chart
    if "bw" in chart_files:
        w(f"![Bodyweight Exercises]({chart_files['bw']})")
        w("")

    # Supporting exercises (detailed/full)
    if report_type in ("detailed", "full"):
        t2_stats = {k: v for k, v in ex_stats.items()
                    if k not in set(t1_order)}
        if t2_stats:
            w("---")
            w("")
            w("## 💪 Supporting Exercises")
            w("")
            w("| Exercise | Best Weight | Best e1RM | Sets | Total Reps |")
            w("|:---------|:----------:|:---------:|:----:|:----------:|")
            for name, st in sorted(t2_stats.items(), key=lambda x: -x[1]["total_sets"]):
                tier = classify_exercise(name, ex_index, t1, t2)
                if tier > 2 and report_type == "detailed":
                    continue
                w(f"| {name} | {st['best_weight']:.0f} kg | {st['best_e1rm']:.0f} kg "
                  f"| {st['total_sets']} | {st['total_reps']} |")
            w("")

    # Recent Sessions
    w("---")
    w("")
    w(f"## 🗓️ Recent Sessions")
    w("")
    if "sessions" in chart_files:
        w(f"![Per-Session Load Breakdown]({chart_files['sessions']})")
        w("")
    for sess in sessions[:n_sessions]:
        label = f"**{sess['date']}**"
        if sess["name"]:
            label += f" — {sess['name']}"
        w(f"### {label}")
        w("")
        w("| Exercise | Sets |")
        w("|:---------|:-----|")
        for ex_name, set_strs in sess["exercises"].items():
            w(f"| {ex_name} | `{', '.join(set_strs)}` |")
        w("")

    # Volume Trends
    if wk_vol:
        w("---")
        w("")
        w("## 📊 Volume Trends")
        w("")
        if "volume" in chart_files:
            w(f"![Weekly Training Volume]({chart_files['volume']})")
            w("")
        w("<details><summary>Weekly data table</summary>")
        w("")
        w("| Week | Load (ψ) | Sessions | Avg load/session |")
        w("|:-----|:--------:|:--------:|:----------------:|")
        for wk in wk_vol[-20:]:
            w(f"| {wk['week']} | {wk['load']:,} | {wk['sessions']} | {wk['avg_load']:,} |")
        w("")
        w("</details>")
        w("")

    # Movement Balance (detailed/full)
    if report_type in ("detailed", "full"):
        total_load = sum(v["load"] for v in balance.values()) or 1
        w("---")
        w("")
        w("## ⚖️ Movement Balance")
        w("")
        if "balance" in chart_files:
            w(f"![Movement Balance]({chart_files['balance']})")
            w("")
        w("| Category | Sets | Load (ψ) | % |")
        w("|:---------|:----:|:--------:|:-:|")
        for cat, vals in balance.items():
            pct = round(vals["load"] / total_load * 100, 1)
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            w(f"| **{cat}** | {vals['sets']} | {vals['load']:,} | {pct}% `{bar}` |")
        w("")

    # Accessory appendix (full only)
    if report_type == "full":
        accessory_sets = [s for s in all_sets
                          if classify_exercise(s["exercise_name"], ex_index, t1, t2) == 3]
        if accessory_sets:
            acc_stats = exercise_stats(accessory_sets)
            w("---")
            w("")
            w("## 📎 Appendix: Accessory Exercises (Tier 3)")
            w("")
            w("> ⚠️ **Not included in volume totals above.** These are isolation/accessory "
              "movements that inflate load metrics disproportionately.")
            w("")
            w("<details><summary>Click to expand</summary>")
            w("")
            w("| Exercise | Sets | Best Weight |")
            w("|:---------|:----:|:-----------:|")
            for name, st in sorted(acc_stats.items(), key=lambda x: -x[1]["total_sets"]):
                w(f"| {name} | {st['total_sets']} | {st['best_weight']:.0f} kg |")
            w("")
            w("</details>")
            w("")

    # Footer
    w("---")
    w("")
    w("> *⚠️ Tier 3 exercises (grip, core, arm isolation) excluded from all aggregations.*  ")
    w(f"> *Generated by `reports/generate_report.py` on {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    report = "\n".join(lines)

    if output:
        Path(output).write_text(report)
        print(f"Report written to {output}", file=sys.stderr)

    return report

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate biovector training reports with charts")
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
