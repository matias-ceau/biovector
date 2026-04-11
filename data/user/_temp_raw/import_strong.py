#!/usr/bin/env python3
"""Import Strong app CSV export into biovector sets.json."""

import csv
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
CSV_PATH = SCRIPT_DIR / "strong_app" / "strong7386152350820285603.csv"
SETS_JSON = SCRIPT_DIR.parent / "sets.json"
BACKUP_PATH = SETS_JSON.with_suffix(".json.bak")

# ── Europe/Paris offset (simplified: UTC+2 for this date range) ──────────────
# The CSV covers 2023-07-14 to 2024-06-29.
# Paris is UTC+2 during CEST (late March → late October) and UTC+1 during CET.
# We use zoneinfo for correct DST handling.
try:
    from zoneinfo import ZoneInfo
    PARIS_TZ = ZoneInfo("Europe/Paris")
except ImportError:
    # Fallback: fixed UTC+2 (will be off by 1h in winter)
    PARIS_TZ = timezone(timedelta(hours=2))

# ── Exercise name mapping ────────────────────────────────────────────────────
EXERCISE_MAP = {
    "Squat (Barbell)": "Squat",
    "Front Squat (Barbell)": "Front Squat",
    "Bench Press (Barbell)": "Bench Press",
    "Deadlift (Barbell)": "Deadlift",
    "Power Clean": "Power Clean",
    "Overhead Press (Barbell)": "Military Press",
    "Chin Up": "Chin Up",
    "Pull Up": "Pull Up",
    "Chest Dip": "Dip",
}

# Regex to strip parenthetical suffixes like " (Barbell)", " (Dumbbell)", etc.
PAREN_SUFFIX = re.compile(r"\s+\([^)]+\)$")


def map_exercise_name(strong_name: str) -> str:
    """Map Strong exercise name to Biovector name."""
    if strong_name in EXERCISE_MAP:
        return EXERCISE_MAP[strong_name]
    return PAREN_SUFFIX.sub("", strong_name)


def parse_timestamp(date_str: str, set_order_offset: int) -> float:
    """Parse Strong date string to Unix timestamp (Europe/Paris TZ).

    Adds set_order_offset seconds to disambiguate sets within same workout.
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=PARIS_TZ)
    return dt.timestamp() + set_order_offset


def is_working_set(set_order: str) -> bool:
    """Return True if this set should be included (numeric or F)."""
    if set_order == "F":
        return True
    try:
        int(set_order)
        return True
    except ValueError:
        return False


def get_set_order_offset(set_order: str) -> int:
    """Get seconds offset from set order for timestamp disambiguation."""
    try:
        return int(set_order)
    except ValueError:
        # "F" → use 0 (will share base timestamp, but that's fine since
        # the exercise name will differ from the numeric-order sets)
        return 0


def main():
    # ── Load existing sets ───────────────────────────────────────────────
    print(f"Loading existing sets from {SETS_JSON}")
    with open(SETS_JSON) as f:
        data = json.load(f)
    existing_sets = data["sets"]
    print(f"  Existing sets: {len(existing_sets)}")

    # ── Build dedup index: (exercise_name, weight, reps) → [timestamps] ──
    dedup_index: dict[tuple[str, float, int], list[float]] = {}
    for s in existing_sets:
        key = (s["exercise_name"], float(s["weight"]), int(s["reps"]))
        dedup_index.setdefault(key, []).append(float(s["timestamp"]))

    def is_duplicate(exercise_name: str, weight: float, reps: int, ts: float) -> bool:
        key = (exercise_name, weight, reps)
        if key not in dedup_index:
            return False
        for existing_ts in dedup_index[key]:
            if abs(existing_ts - ts) <= 120:
                return True
        return False

    # ── Parse CSV ────────────────────────────────────────────────────────
    print(f"Parsing CSV: {CSV_PATH}")
    total_rows = 0
    skipped_set_order = 0
    skipped_empty = 0
    duplicates = 0
    new_sets = []

    filter_reasons: dict[str, int] = {"W": 0, "D": 0, "Note": 0}

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";", quotechar='"')
        for row in reader:
            total_rows += 1
            set_order = row["Set Order"].strip()

            # Filter by set order
            if not is_working_set(set_order):
                skipped_set_order += 1
                if set_order in filter_reasons:
                    filter_reasons[set_order] += 1
                continue

            # Parse weight and reps
            weight_str = row["Weight (kg)"].strip()
            reps_str = row["Reps"].strip()

            weight = float(weight_str) if weight_str else 0.0
            reps = int(reps_str) if reps_str else 0

            # Skip if both are empty/zero
            if weight == 0.0 and reps == 0:
                skipped_empty += 1
                continue

            # Map exercise name
            exercise_name = map_exercise_name(row["Exercise Name"].strip())

            # Compute timestamp
            offset = get_set_order_offset(set_order)
            ts = parse_timestamp(row["Date"].strip(), offset)

            # Check for duplicates
            if is_duplicate(exercise_name, weight, reps, ts):
                duplicates += 1
                continue

            # Build set record
            session_name = row["Workout Name"].strip()
            notes_parts = []
            if set_order == "F":
                notes_parts.append("FAILED")
            if row["Notes"].strip():
                notes_parts.append(row["Notes"].strip())
            notes = ": ".join(notes_parts) if notes_parts else ""

            new_set: dict = {
                "timestamp": ts,
                "exercise_name": exercise_name,
                "weight": weight,
                "reps": reps,
                "session_name": session_name,
            }
            if notes:
                new_set["notes"] = notes

            new_sets.append(new_set)

            # Add to dedup index so we don't double-import within the CSV itself
            key = (exercise_name, weight, reps)
            dedup_index.setdefault(key, []).append(ts)

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"CSV IMPORT SUMMARY")
    print(f"{'='*60}")
    print(f"Total CSV data rows:      {total_rows}")
    print(f"Filtered out (set order): {skipped_set_order}")
    for reason, count in sorted(filter_reasons.items()):
        if count > 0:
            print(f"  - {reason}: {count}")
    print(f"Filtered out (no weight/reps): {skipped_empty}")
    print(f"Duplicates skipped:       {duplicates}")
    print(f"New sets to add:          {len(new_sets)}")

    if new_sets:
        ts_min = min(s["timestamp"] for s in new_sets)
        ts_max = max(s["timestamp"] for s in new_sets)
        print(f"Date range of new sets:   {datetime.fromtimestamp(ts_min)} → {datetime.fromtimestamp(ts_max)}")

        # Count by exercise
        exercise_counts: dict[str, int] = {}
        for s in new_sets:
            exercise_counts[s["exercise_name"]] = exercise_counts.get(s["exercise_name"], 0) + 1
        print(f"\nSets by exercise:")
        for ex, count in sorted(exercise_counts.items(), key=lambda x: -x[1]):
            print(f"  {ex}: {count}")
    print(f"{'='*60}")

    if not new_sets:
        print("\nNo new sets to add. Exiting without modifying sets.json.")
        return

    # ── Backup ───────────────────────────────────────────────────────────
    print(f"\nBacking up {SETS_JSON} → {BACKUP_PATH}")
    shutil.copy2(SETS_JSON, BACKUP_PATH)

    # ── Merge and write ──────────────────────────────────────────────────
    all_sets = existing_sets + new_sets
    all_sets.sort(key=lambda s: s["timestamp"])
    data["sets"] = all_sets

    print(f"Writing {len(all_sets)} total sets to {SETS_JSON}")
    with open(SETS_JSON, "w") as f:
        json.dump(data, f, indent=2)
    print("Done.")


if __name__ == "__main__":
    main()
