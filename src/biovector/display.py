"""Display utilities for biovector data."""

from __future__ import annotations

import datetime
from biovector.core import Biovector, epley


def format_session_summary(bv: Biovector, session_id: str) -> str:
    """Format a session summary as a readable string."""
    session = next((s for s in bv.sessions if s["id"] == session_id), None)
    if not session:
        return f"Session {session_id} not found."

    sets = bv.session_sets(session_id)
    if not sets:
        return f"No sets found for session {session_id}."

    start = datetime.datetime.fromtimestamp(session["start_timestamp"])
    end = datetime.datetime.fromtimestamp(session["end_timestamp"])
    duration = end - start

    lines = [
        "=" * 60,
        f"  Session: {session.get('name', session_id)}",
        f"  Date: {start.strftime('%Y-%m-%d %H:%M')}",
        f"  Duration: {str(duration).split('.')[0]}",
        f"  Sets: {len(sets)}  |  Exercises: {len(session['exercises'])}",
        "=" * 60,
        f"  {'Exercise':<20} {'W':>5} {'R':>3} {'1RM':>5}",
        "-" * 60,
    ]

    for s in sets:
        pred_1rm = round(epley(s["weight"], s["reps"]), 1)
        lines.append(
            f"  {s['exercise_name']:<20} {s['weight']:>5.0f} {s['reps']:>3d} {pred_1rm:>5.0f}"
        )

    lines.append("=" * 60)
    return "\n".join(lines)


def format_exercise_stats(bv: Biovector, exercise_name: str) -> str:
    """Format statistics for an exercise as a readable string."""
    history = bv.exercise_1rm_history(exercise_name)
    if not history:
        return f"No data found for {exercise_name}."

    best = max(history, key=lambda h: h["pred_1rm"])
    recent = history[-1]
    total_sets = len(history)

    lines = [
        f"  Exercise: {exercise_name}",
        f"  Total sets: {total_sets}",
        f"  Best 1RM: {best['pred_1rm']} kg ({best['date']})",
        f"  Latest: {recent['weight']}kg x {recent['reps']} = {recent['pred_1rm']}kg 1RM ({recent['date']})",
    ]
    return "\n".join(lines)
