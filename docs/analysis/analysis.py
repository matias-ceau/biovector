#!/usr/bin/env python3
"""Analysis of biovector workout data."""

import csv
from datetime import datetime
from collections import defaultdict
import statistics

# Read workouts
workouts = []
with open("src/biovector/data/workouts.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        workouts.append(
            {
                "number": float(row["Number"]),
                "date": datetime.fromtimestamp(float(row["Timestamp"])),
                "hardsets": float(row["Hardsets"]),
                "load": float(row["Load"]),
                "hardload": float(row["Hardload"]),
            }
        )

# Read sets
sets = []
with open("src/biovector/data/sets.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            sets.append(
                {
                    "timestamp": float(row["Timestamp"]),
                    "date": datetime.fromtimestamp(float(row["Timestamp"])),
                    "workout": row["Workout Name"],
                    "exercise": row["Exercise Name"],
                    "exercise_id": row["ID"],
                    "weight": float(row["Weight"]),
                    "reps": float(row["Reps"]),
                    "user_weight": float(row["User Weight"]),
                    "intensity": float(row["Int"]) if row["Int"] else 0,
                    "h": float(row["h"]) if row["h"] else 0,
                    "load": float(row["Load"]) if row["Load"] else 0,
                    "phi": float(row["phi"]) if row["phi"] else 0,
                }
            )
        except (ValueError, KeyError):
            continue

# Read exercises
exercises = {}
with open("src/biovector/data/exercises.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        exercises[row["ID"]] = {
            "name": row["Exercise"],
            "short": row["Short"],
            "delta": float(row["Delta"]),
            "rho": float(row["rho"]),
            "theta": float(row["theta"]),
            "type": row["Type"],
        }

print("=" * 60)
print("BIOVECTOR WORKOUT DATA ANALYSIS")
print("=" * 60)

# Time range
first_workout = min(s["date"] for s in sets)
last_workout = max(s["date"] for s in sets)
days_span = (last_workout - first_workout).days

print("\n📅 TIME RANGE")
print(f"   First workout: {first_workout.strftime('%Y-%m-%d')}")
print(f"   Last workout:  {last_workout.strftime('%Y-%m-%d')}")
print(f"   Total span:    {days_span} days (~{days_span / 365:.1f} years)")

# Workout frequency
print("\n📊 WORKOUT STATISTICS")
print(f"   Total workouts: {len(workouts)}")
print(f"   Total sets:     {len(sets)}")
print(f"   Sets/workout:   {len(sets) / len(workouts):.1f}")
print(f"   Workouts/month: {len(workouts) / (days_span / 30):.1f}")

# Volume trends
print("\n🏋️ VOLUME ANALYSIS")
total_load = sum(w["load"] for w in workouts)
total_hardload = sum(w["hardload"] for w in workouts)
total_hardsets = sum(w["hardsets"] for w in workouts)

print(f"   Total Standardized Volume (Ψ): {total_load:,.0f} kg·m")
print(f"   Total Hard Set Volume (Φ):     {total_hardload:,.0f} kg·m")
print(f"   Total Hard Sets (N):           {total_hardsets:.0f}")
print(f"   Hard set ratio (Φ/Ψ):          {total_hardload / total_load:.2%}")

# By exercise type
exercise_stats: defaultdict[str, dict[str, float]] = defaultdict(
    lambda: {"sets": 0, "load": 0, "phi": 0, "max_weight": 0}
)
for s in sets:
    ex = s["exercise"]
    exercise_stats[ex]["sets"] += 1
    exercise_stats[ex]["load"] += s["load"]
    exercise_stats[ex]["phi"] += s["phi"]
    exercise_stats[ex]["max_weight"] = max(exercise_stats[ex]["max_weight"], s["weight"])

# Top exercises by volume
print("\n🔥 TOP EXERCISES BY VOLUME")
sorted_ex = sorted(exercise_stats.items(), key=lambda x: x[1]["load"], reverse=True)[:10]
for ex, stats in sorted_ex:
    print(f"   {ex:25s}: {stats['load']:>8,.0f} kg·m ({stats['sets']} sets)")

# Strength progression for main lifts
main_lifts = ["Squat", "Deadlift", "Bench Press", "Military Press", "Chin Up"]
print("\n📈 MAIN LIFT PROGRESSION (max weight by month)")

for lift in main_lifts:
    lift_sets = [s for s in sets if s["exercise"] == lift and s["weight"] > 0]
    if not lift_sets:
        continue

    # Group by month
    monthly_max: defaultdict[str, float] = defaultdict(float)
    for s in lift_sets:
        month_key = s["date"].strftime("%Y-%m")
        monthly_max[month_key] = max(monthly_max[month_key], s["weight"])

    sorted_months = sorted(monthly_max.items())
    if len(sorted_months) >= 2:
        first = sorted_months[0][1]
        last = sorted_months[-1][1]
        print(f"\n   {lift}:")
        print(f"      First recorded: {first:.1f} kg")
        print(f"      Last recorded:  {last:.1f} kg")
        print(f"      Progress:       {last - first:+.1f} kg ({(last / first - 1) * 100:+.1f}%)")
        if len(sorted_months) > 1:
            # Show peak
            peak_month, peak_val = max(sorted_months, key=lambda x: x[1])
            print(f"      Peak:           {peak_val:.1f} kg ({peak_month})")

# Bodyweight tracking
print("\n⚖️ BODYWEIGHT TRACKING")
user_weights = [s["user_weight"] for s in sets]
print(f"   Min:  {min(user_weights):.1f} kg")
print(f"   Max:  {max(user_weights):.1f} kg")
print(f"   Mean: {statistics.mean(user_weights):.1f} kg")

# Intensity distribution
print("\n📉 INTENSITY DISTRIBUTION")
intensity_ranges = {"<50%": 0, "50-75%": 0, "75-85%": 0, "85-95%": 0, ">95%": 0}
for s in sets:
    i = s["intensity"]
    if i < 0.5:
        intensity_ranges["<50%"] += 1
    elif i < 0.75:
        intensity_ranges["50-75%"] += 1
    elif i < 0.85:
        intensity_ranges["75-85%"] += 1
    elif i < 0.95:
        intensity_ranges["85-95%"] += 1
    else:
        intensity_ranges[">95%"] += 1

total = sum(intensity_ranges.values())
for range_name, count in intensity_ranges.items():
    pct = count / total * 100
    bar = "█" * int(pct / 2)
    print(f"   {range_name:8s}: {count:>5d} sets ({pct:>5.1f}%) {bar}")

# Recent activity
print("\n🕐 RECENT ACTIVITY (last 5 workouts)")
recent = sorted(workouts, key=lambda x: x["date"], reverse=True)[:5]
for w in recent:
    print(
        f"   {w['date'].strftime('%Y-%m-%d')}: Hardsets={w['hardsets']:>5.1f}, Load={w['load']:>8.0f}, Φ={w['hardload']:>8.0f}"
    )

print("\n" + "=" * 60)
