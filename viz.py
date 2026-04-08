#!/usr/bin/env python3
"""Generate training visualization charts for GitHub."""

import csv
from datetime import datetime
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Paths
REPO_ROOT = Path(__file__).parent
DATA_DIR = REPO_ROOT / "src/biovector/data"
REPORTS_DIR = REPO_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def load_data():
    """Load workouts and sets data."""
    workouts = []
    with open(DATA_DIR / "workouts.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                workouts.append({
                    "number": float(row["Number"]),
                    "date": datetime.fromtimestamp(float(row["Timestamp"])),
                    "hardsets": float(row["Hardsets"]),
                    "load": float(row["Load"]),
                    "hardload": float(row["Hardload"]),
                })
            except (ValueError, KeyError):
                continue

    sets = []
    with open(DATA_DIR / "sets.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                sets.append({
                    "timestamp": float(row["Timestamp"]),
                    "date": datetime.fromtimestamp(float(row["Timestamp"])),
                    "workout": row["Workout Name"],
                    "exercise": row["Exercise Name"],
                    "weight": float(row["Weight"]),
                    "reps": float(row["Reps"]),
                    "load": float(row["Load"]) if row["Load"] else 0,
                })
            except (ValueError, KeyError):
                continue

    return workouts, sets


def plot_main_lifts(sets):
    """Plot progression for main lifts."""
    main_lifts = ["Squat", "Deadlift", "Bench Press", "Front Squat", "Military Press"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    for idx, lift in enumerate(main_lifts):
        ax = axes[idx]
        lift_sets = [s for s in sets if s["exercise"] == lift and s["weight"] > 0]

        if not lift_sets:
            ax.text(0.5, 0.5, f"No data for {lift}", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(lift)
            ax.axis('off')
            continue

        monthly_max = defaultdict(float)
        for s in lift_sets:
            month_key = s["date"].strftime("%Y-%m")
            monthly_max[month_key] = max(monthly_max[month_key], s["weight"])

        sorted_months = sorted(monthly_max.items())
        dates = [datetime.strptime(m, "%Y-%m") for m, _ in sorted_months]
        weights = [w for _, w in sorted_months]

        ax.plot(dates, weights, marker="o", linewidth=2, markersize=4)
        ax.set_title(f"{lift} - Max Weight", fontsize=12, fontweight="bold")
        ax.set_xlabel("Date")
        ax.set_ylabel("Weight (kg)")
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fig.delaxes(axes[5])
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "main_lifts.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"✓ Saved reports/main_lifts.png")


def plot_volume_trends(workouts):
    """Plot volume trends over time."""
    if not workouts:
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

    dates = [w["date"] for w in workouts]
    loads = [w["load"] for w in workouts]
    hardloads = [w["hardload"] for w in workouts]

    ax1.plot(dates, loads, marker="o", markersize=3, linewidth=1, alpha=0.7)
    ax1.set_title("Total Volume (Ψ) Over Time", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Load (kg·m)")
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    ax2.plot(dates, hardloads, marker="o", markersize=3, linewidth=1, alpha=0.7, color="red")
    ax2.set_title("Hard Set Volume (Φ) Over Time", fontsize=12, fontweight="bold")
    ax2.set_ylabel("Hardload (kg·m)")
    ax2.set_xlabel("Date")
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "volume_trends.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"✓ Saved reports/volume_trends.png")


def plot_exercise_distribution(sets):
    """Plot exercise distribution by volume."""
    exercise_stats = defaultdict(lambda: {"load": 0})
    for s in sets:
        ex = s["exercise"]
        exercise_stats[ex]["load"] += s["load"]

    sorted_ex = sorted(exercise_stats.items(), key=lambda x: x[1]["load"], reverse=True)[:10]
    exercises = [ex for ex, _ in sorted_ex]
    volumes = [stats["load"] for _, stats in sorted_ex]

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.barh(exercises[::-1], volumes[::-1], color="steelblue")
    ax.set_title("Top 10 Exercises by Volume", fontsize=12, fontweight="bold")
    ax.set_xlabel("Total Volume (kg·m)")
    ax.grid(True, alpha=0.3, axis="x")
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "exercise_distribution.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"✓ Saved reports/exercise_distribution.png")


def generate_summary_md(workouts, sets):
    """Generate a markdown summary report."""
    if not workouts:
        return "# Biovector Report\n\nNo data available."

    first_workout = min(s["date"] for s in sets)
    last_workout = max(s["date"] for s in sets)
    days_span = (last_workout - first_workout).days

    total_load = sum(w["load"] for w in workouts)
    total_hardload = sum(w["hardload"] for w in workouts)

    recent = sorted(workouts, key=lambda x: x["date"], reverse=True)[:5]
    recent_table = "| Date | Hardsets | Load | Hardload |\n|---|---|---|---|\n"
    for w in recent:
        recent_table += f"| {w['date'].strftime('%Y-%m-%d')} | {w['hardsets']:.1f} | {w['load']:,.0f} | {w['hardload']:,.0f} |\n"

    md = f"""# Biovector Training Report

**Data range:** {first_workout.strftime('%Y-%m-%d')} to {last_workout.strftime('%Y-%m-%d')} ({days_span} days)

## Summary Stats

- **Total Volume (Ψ):** {total_load:,.0f} kg·m
- **Total Hardload (Φ):** {total_hardload:,.0f} kg·m
- **Workouts:** {len(workouts)}
- **Sets:** {len(sets)}

## Recent Workouts

{recent_table}

## Charts

![Main Lifts](main_lifts.png)
![Volume Trends](volume_trends.png)
![Exercise Distribution](exercise_distribution.png)

---
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

    with open(REPORTS_DIR / "README.md", "w") as f:
        f.write(md)
    print(f"✓ Saved reports/README.md")


def main():
    print("Generating biovector visualizations...")
    workouts, sets = load_data()
    print(f"Loaded {len(workouts)} workouts, {len(sets)} sets")

    if not workouts:
        print("No data to visualize.")
        return

    plot_main_lifts(sets)
    plot_volume_trends(workouts)
    plot_exercise_distribution(sets)
    generate_summary_md(workouts, sets)

    print(f"\nAll reports saved to: {REPORTS_DIR}")


if __name__ == "__main__":
    main()
