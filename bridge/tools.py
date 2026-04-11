"""Tool implementations for the biovector MCP server."""

from __future__ import annotations

import json
import datetime
import sys
from pathlib import Path

# Add src to path so we can import biovector
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from biovector.core import Biovector, epley
from biovector.stats import recent_1rm_by_exercise, exercise_frequency, weekly_volume
from biovector.display import format_session_summary, format_exercise_stats

# Singleton instance
_bv: Biovector | None = None


def get_bv() -> Biovector:
    global _bv
    if _bv is None:
        _bv = Biovector()
    return _bv


def add_set(exercise_name: str, weight: float, reps: int,
            session_name: str = "", notes: str = "") -> str:
    """Log a new exercise set.
    
    Args:
        exercise_name: Name, short code, or ID of the exercise
        weight: Weight in kg
        reps: Number of repetitions
        session_name: Optional session/workout name
        notes: Optional notes
    
    Returns:
        Confirmation message with set details and predicted 1RM.
    """
    bv = get_bv()
    ex = bv.get_exercise(exercise_name)
    if not ex:
        return f"Error: Unknown exercise '{exercise_name}'. Use list_exercises to find valid names."
    
    entry = bv.add_set(ex["name"], weight, reps, session_name, notes)
    pred_1rm = round(epley(weight, reps), 1)
    return (f"Set logged: {ex['name']} — {weight}kg × {reps} reps "
            f"(estimated 1RM: {pred_1rm}kg)")


def get_workout_history(exercise_name: str = "", days: int = 90,
                        limit: int = 20) -> str:
    """Retrieve workout history, optionally filtered by exercise.
    
    Args:
        exercise_name: Filter by exercise name (empty for all)
        days: Number of days to look back
        limit: Maximum number of sets to return
    
    Returns:
        Formatted workout history.
    """
    bv = get_bv()
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp()
    
    if exercise_name:
        ex = bv.get_exercise(exercise_name)
        if not ex:
            return f"Unknown exercise: {exercise_name}"
        sets = [s for s in bv.sets_for_exercise(ex["name"]) if s["timestamp"] >= cutoff]
    else:
        sets = [s for s in bv.sets if s["timestamp"] >= cutoff]
    
    sets = sorted(sets, key=lambda s: s["timestamp"], reverse=True)[:limit]
    
    if not sets:
        return "No sets found in the specified period."
    
    lines = [f"Last {len(sets)} sets (past {days} days):", ""]
    for s in sets:
        dt = datetime.datetime.fromtimestamp(s["timestamp"]).strftime("%Y-%m-%d %H:%M")
        pred = round(epley(s["weight"], s["reps"]), 1)
        lines.append(f"  {dt}  {s['exercise_name']:<20} {s['weight']:>5.0f}kg × {s['reps']:>2d}  (1RM: {pred}kg)")
    
    return "\n".join(lines)


def get_exercise_stats(exercise_name: str, days: int = 90) -> str:
    """Get statistics and progression for a specific exercise.
    
    Args:
        exercise_name: Exercise name, short code, or ID
        days: Lookback period
    
    Returns:
        Exercise statistics summary.
    """
    bv = get_bv()
    ex = bv.get_exercise(exercise_name)
    if not ex:
        return f"Unknown exercise: {exercise_name}"
    return format_exercise_stats(bv, ex["name"])


def get_1rm_progression(exercise_name: str, limit: int = 20) -> str:
    """Track estimated 1RM progression over time.
    
    Args:
        exercise_name: Exercise name
        limit: Max data points
    
    Returns:
        1RM history showing progression.
    """
    bv = get_bv()
    ex = bv.get_exercise(exercise_name)
    if not ex:
        return f"Unknown exercise: {exercise_name}"
    
    history = bv.exercise_1rm_history(ex["name"])
    if not history:
        return f"No data for {ex['name']}."
    
    # Sample evenly if too many points
    if len(history) > limit:
        step = len(history) // limit
        history = history[::step] + [history[-1]]
    
    lines = [f"1RM Progression for {ex['name']}:", ""]
    for h in history:
        lines.append(f"  {h['date']}  {h['pred_1rm']:>6.1f}kg  (best: {h['best_1rm']:.1f}kg)")
    
    return "\n".join(lines)


def get_recent_sessions(limit: int = 5) -> str:
    """Get the most recent workout sessions.
    
    Args:
        limit: Number of sessions to return
    
    Returns:
        Summary of recent sessions.
    """
    bv = get_bv()
    sessions = bv.recent_sessions(limit)
    
    if not sessions:
        return "No sessions found."
    
    lines = [f"Last {len(sessions)} sessions:", ""]
    for s in sessions:
        dt = datetime.datetime.fromtimestamp(s["start_timestamp"]).strftime("%Y-%m-%d")
        exercises = ", ".join(s["exercises"][:4])
        if len(s["exercises"]) > 4:
            exercises += f" +{len(s['exercises']) - 4} more"
        lines.append(f"  {dt}  {s.get('name', 'unnamed'):<20} {s['set_count']} sets — {exercises}")
    
    return "\n".join(lines)


def get_session_detail(session_id: str) -> str:
    """Get detailed information about a specific session.
    
    Args:
        session_id: Session ID (e.g. session_20180212_150054)
    
    Returns:
        Detailed session breakdown.
    """
    bv = get_bv()
    return format_session_summary(bv, session_id)


def list_exercises(category: str = "", search: str = "") -> str:
    """List available exercises, optionally filtered.
    
    Args:
        category: Filter by type (Barbell, Bodyweight, Dumbell, Kettlebell, etc.)
        search: Search string to match against name/short/ID
    
    Returns:
        Formatted exercise list.
    """
    bv = get_bv()
    results = bv.list_exercises(category, search)
    
    if not results:
        return "No exercises found matching your criteria."
    
    lines = [f"Exercises ({len(results)} found):", ""]
    for ex in results:
        short = f" ({ex['short']})" if ex.get("short") else ""
        lines.append(f"  {ex['id']:<10} {ex['name']}{short}  [{ex['type']}]")
    
    return "\n".join(lines)


def get_weekly_summary(weeks: int = 8) -> str:
    """Get weekly training volume summary.
    
    Args:
        weeks: Number of weeks to summarize
    
    Returns:
        Weekly volume breakdown.
    """
    bv = get_bv()
    data = weekly_volume(bv, weeks)
    
    if not data:
        return "No data for the specified period."
    
    lines = [f"Weekly Volume (last {weeks} weeks):", ""]
    for w in data:
        lines.append(f"  {w['week']}  {w['sets']:>3d} sets  {w['load']:>8,.0f} kg·reps")
    
    return "\n".join(lines)


def get_strength_overview(days: int = 90) -> str:
    """Overview of current strength levels across main exercises.
    
    Args:
        days: Lookback period
    
    Returns:
        Best recent 1RM for each exercise.
    """
    bv = get_bv()
    best = recent_1rm_by_exercise(bv, days)
    
    if not best:
        return "No data found."
    
    top = sorted(best.items(), key=lambda x: x[1], reverse=True)[:15]
    lines = [f"Strength Overview (best 1RM, last {days} days):", ""]
    for name, rm in top:
        lines.append(f"  {name:<25} {rm:>6.1f} kg")
    
    return "\n".join(lines)
