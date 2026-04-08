import argparse, sys
import datetime

from . import bv_utils, stats, workout, interactive


class Main():
    """Main object, redirects user inputs into different modules and functions."""

    def __init__(self):
        self.info = '\n'.join(f"   {k:<15}   {str(v.__doc__)}" for k,v in Main.__dict__.items() if k[0]!='_')
        parser = argparse.ArgumentParser(prog=('biovector'),
                                         description='biovector',
                                         usage=f'''bv <command> [<args>]

{self.info}
                             ''')
        parser.add_argument('command', help='Subcommand to run')
        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print('Unrecognized command')
            parser.print_help()
            exit(1)
        getattr(self, args.command)()

    def sets(self):
        """Show, modify or add sets."""
        parser = argparse.ArgumentParser(description=self.sets.__doc__)
        subparsers = parser.add_subparsers(dest='sets')

        add_parser = subparsers.add_parser('add')
        add_parser.add_argument('sets',nargs='+')

        ls_parser = subparsers.add_parser('ls')
        ls_parser.add_argument('--verbose','-v',action='count')

        mod_parser = subparsers.add_parser('mod')
        mod_parser.add_argument('mod')

        del_parser = subparsers.add_parser('del')
        del_parser.add_argument('del')

        args = parser.parse_args(sys.argv[2:])
        print(args)
        # option -0 don't count
        # destination

    def workout(self):
        """Initialize new workout, visualize current workouts."""
        parser = argparse.ArgumentParser(description=self.workout.__doc__)
        subparsers = parser.add_subparsers(dest='workout')

        ls_parser = subparsers.add_parser('ls')

        new_parser = subparsers.add_parser('new')
        new_parser.add_argument('new')

        args = parser.parse_args(sys.argv[2:])
        print(args)

    def measures(self):
        """View or modify measures."""
        parser = argparse.ArgumentParser(description=self.measures.__doc__)
        subparsers = parser.add_subparsers(dest='measures')

        measures_parser = subparsers.add_parser('add')
        measures_parser = subparsers.add_parser('ls')
        # option bw neck etc
        args = parser.parse_args(sys.argv[2:])
        print(args)

    def program(self):
        """Interact with programs."""
        parser = argparse.ArgumentParser(description=self.program.__doc__)
        subparsers = parser.add_subparsers(dest='program')

        program_parser = subparsers.add_parser()
        program_parser.add_argument('show')

        program_parser.add_argument('ls')

        program_parser.add_argument('create')
        args = parser.parse_args(sys.argv[2:])
        print(args)

    def exercise(self):
        """Create or see last sets for a specific exercise."""
        parser = argparse.ArgumentParser(description=self.exercise.__doc__)
        subparsers = parser.add_subparsers(dest='exercise')

        program_parser = subparsers.add_parser()
        program_parser.add_argument('show')

        program_parser.add_argument('ls')

        program_parser.add_argument('create')
        args = parser.parse_args(sys.argv[2:])
        print(args)

    def interactive(self):
        """Interactive CLI mode."""
        interactive.main()

    def config(self):
        """Modify user configuration."""
        parser = argparse.ArgumentParser(description=self.config.__doc__)
        parser.add_argument('--thing')
        #TM, current program
        args = parser.parse_args(sys.argv[2:])
        print(args)

    def update(self):
        """Recalculate values."""
        parser = argparse.ArgumentParser(description=self.update.__doc__)
        #update all, update specific
        parser.add_argument('--all', '-a',action='store_true')
        args = parser.parse_args(sys.argv[2:])
        print(args)
        if args.all:
            bv_utils.Updater().update_all()

    def stats(self):
        """Show statistics."""
        parser = argparse.ArgumentParser(description=self.stats.__doc__)
        #1rm weekly yearly
        parser.add_argument('--rm')
        args = parser.parse_args(sys.argv[2:])
        print(args)

    def cardio(self):
        """Log cardio activity."""
        parser = argparse.ArgumentParser(description=self.cardio.__doc__)
        parser.add_argument("name")
        parser.add_argument("--type", default="run")
        parser.add_argument("--duration", type=int, required=True, help="Duration in seconds")
        parser.add_argument("--distance", type=float, default=0.0, help="Distance in km")
        parser.add_argument("--hr", type=float, default=0.0, help="Average heart rate")
        parser.add_argument("--calories", type=float, default=0.0)
        parser.add_argument("--notes", default="")
        args = parser.parse_args(sys.argv[2:])

        bio = bv_utils.Biovector(selected=["cardio"])
        bio.append_record("cardio", {
            "Timestamp": datetime.datetime.now().timestamp(),
            "Date": str(datetime.datetime.now())[:-7],
            "Workout Name": args.name,
            "Type": args.type,
            "DurationSec": args.duration,
            "DistanceKm": args.distance,
            "AvgHeartRate": args.hr,
            "Calories": args.calories,
            "Notes": args.notes,
        })
        print("Cardio entry added.")

    def kettlebell(self):
        """Log kettlebell activity."""
        parser = argparse.ArgumentParser(description=self.kettlebell.__doc__)
        parser.add_argument("name")
        parser.add_argument("--exercise", required=True)
        parser.add_argument("--weight", type=float, required=True, help="Weight in kg")
        parser.add_argument("--reps", type=int, required=True)
        parser.add_argument("--sets", type=int, default=1)
        parser.add_argument("--style", default="standard", help="e.g. emom, amrap, ladder")
        parser.add_argument("--duration", type=int, default=0, help="Optional duration in seconds")
        parser.add_argument("--notes", default="")
        args = parser.parse_args(sys.argv[2:])

        bio = bv_utils.Biovector(selected=["kettlebell"])
        bio.append_record("kettlebell", {
            "Timestamp": datetime.datetime.now().timestamp(),
            "Date": str(datetime.datetime.now())[:-7],
            "Workout Name": args.name,
            "Exercise": args.exercise,
            "WeightKg": args.weight,
            "Reps": args.reps,
            "Sets": args.sets,
            "Style": args.style,
            "DurationSec": args.duration,
            "Notes": args.notes,
        })
        print("Kettlebell entry added.")

    def import_data(self):
        """Import CSV from external source into biovector data."""
        parser = argparse.ArgumentParser(description=self.import_data.__doc__)
        parser.add_argument("--source", required=True, help="Source label, e.g. garmin, strava, hevy")
        parser.add_argument("--file", required=True, help="Path to CSV file")
        parser.add_argument("--target", required=True, choices=["cardio", "kettlebell", "sets"])
        args = parser.parse_args(sys.argv[2:])

        bio = bv_utils.Biovector(selected=[args.target, "imports"])
        count = bio.import_records_from_csv(args.source, args.file, args.target)
        print(f"Imported {count} rows into {args.target}.")

    def ocr(self):
        """Ingest OCR note text and classify it."""
        parser = argparse.ArgumentParser(description=self.ocr.__doc__)
        parser.add_argument("--source-image", required=True)
        parser.add_argument("--text", required=True, help="OCR extracted text")
        args = parser.parse_args(sys.argv[2:])

        parsed_type, confidence = bv_utils.Biovector.parse_ocr_text(args.text)
        bio = bv_utils.Biovector(selected=["ocr_notes"])
        bio.add_ocr_note(
            source_image=args.source_image,
            raw_text=args.text,
            parsed_type=parsed_type,
            confidence=confidence,
            status="pending_review",
            notes="",
        )
        print(f"OCR note ingested as {parsed_type} (confidence={confidence}).")

    def viz(self):
        """Generate training visualization charts."""
        from pathlib import Path
        import csv
        from datetime import datetime
        from collections import defaultdict
        
        import numpy as np
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        
        PACKAGE_DIR = Path(__file__).resolve().parent
        DATA_DIR = bv_utils.Biovector.resolve_data_dir()
        REPORTS_DIR = PACKAGE_DIR.parent.parent / "reports"
        REPORTS_DIR.mkdir(exist_ok=True)

        def load_data():
            workouts = []
            workouts_path = DATA_DIR / "workouts.csv"
            if workouts_path.exists():
                with open(workouts_path, "r") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            workouts.append({
                                "date": datetime.fromtimestamp(float(row["Timestamp"])),
                                "hardsets": float(row["Hardsets"]),
                                "load": float(row["Load"]),
                                "hardload": float(row["Hardload"]),
                            })
                        except (ValueError, KeyError):
                            continue

            sets = []
            sets_path = DATA_DIR / "sets.csv"
            if sets_path.exists():
                with open(sets_path, "r") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            sets.append({
                                "date": datetime.fromtimestamp(float(row["Timestamp"])),
                                "exercise": row["Exercise Name"],
                                "weight": float(row["Weight"]),
                                "load": float(row["Load"]) if row["Load"] else 0,
                            })
                        except (ValueError, KeyError):
                            continue
            return workouts, sets

        print("Generating visualizations...")
        workouts, sets = load_data()
        print(f"Loaded {len(workouts)} workouts, {len(sets)} sets")

        if not workouts:
            print("No data to visualize.")
            return

        # Main lifts progression
        main_lifts = ["Squat", "Deadlift", "Bench Press", "Front Squat", "Military Press"]
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()
        for idx, lift in enumerate(main_lifts):
            ax = axes[idx]
            lift_sets = [s for s in sets if s["exercise"] == lift and s["weight"] > 0]
            if not lift_sets:
                ax.text(0.5, 0.5, f"No data", ha="center", va="center", transform=ax.transAxes)
                ax.set_title(lift)
                continue
            monthly_max = defaultdict(float)
            for s in lift_sets:
                month_key = s["date"].strftime("%Y-%m")
                monthly_max[month_key] = max(monthly_max[month_key], s["weight"])
            sorted_months = sorted(monthly_max.items())
            dates = [datetime.strptime(m, "%Y-%m") for m, _ in sorted_months]
            weights = [w for _, w in sorted_months]
            ax.plot(dates, weights, marker="o", linewidth=2, markersize=4)
            ax.set_title(f"{lift}", fontsize=12, fontweight="bold")
            ax.set_ylabel("Weight (kg)")
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        fig.delaxes(axes[5])
        plt.tight_layout()
        plt.savefig(REPORTS_DIR / "main_lifts.png", dpi=150, bbox_inches="tight")
        plt.close()
        print(f"✓ reports/main_lifts.png")

        # Volume trends - discrete values with MA10 on secondary axis
        fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
        
        dates = np.array([w["date"] for w in workouts])
        hardsets = np.array([w["hardsets"] for w in workouts])
        loads_t = np.array([w["load"] / 1000 for w in workouts])  # tonne·m
        hardloads_t = np.array([w["hardload"] / 1000 for w in workouts])  # tonne·m
        
        # Rolling average (window=10)
        def rolling_avg(arr, window=10):
            ret = np.cumsum(arr, dtype=float)
            ret[window:] = ret[window:] - ret[:-window]
            ret[:window-1] = ret[:window-1] / np.arange(1, window)
            ret[window-1:] = ret[window-1:] / window
            return ret
        
        # Hardsets (H)
        ax = axes[0]
        ax.scatter(dates, hardsets, s=15, alpha=0.5, color="green", label="H")
        ax2 = ax.twinx()
        ax2.plot(dates, rolling_avg(hardsets), color="darkgreen", linewidth=2, label="H MA10")
        ax2.set_ylabel("H MA10", color="darkgreen")
        ax2.tick_params(axis='y', labelcolor="darkgreen")
        ax.set_title("Hard Sets (H) per Workout", fontsize=12, fontweight="bold")
        ax.set_ylabel("Hard Sets")
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        
        # Load (Ψ)
        ax = axes[1]
        ax.scatter(dates, loads_t, s=15, alpha=0.5, color="orange", label="Ψ")
        ax2 = ax.twinx()
        ax2.plot(dates, rolling_avg(loads_t), color="darkorange", linewidth=2, label="Ψ MA10")
        ax2.set_ylabel("Ψ MA10 (t·m)", color="darkorange")
        ax2.tick_params(axis='y', labelcolor="darkorange")
        ax.set_title("Volume (Ψ) per Workout", fontsize=12, fontweight="bold")
        ax.set_ylabel("Load (t·m)")
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        
        # Hardload (Φ)
        ax = axes[2]
        ax.scatter(dates, hardloads_t, s=15, alpha=0.5, color="red", label="Φ")
        ax2 = ax.twinx()
        ax2.plot(dates, rolling_avg(hardloads_t), color="darkred", linewidth=2, label="Φ MA10")
        ax2.set_ylabel("Φ MA10 (t·m)", color="darkred")
        ax2.tick_params(axis='y', labelcolor="darkred")
        ax.set_title("Hard Set Volume (Φ) per Workout", fontsize=12, fontweight="bold")
        ax.set_ylabel("Hardload (t·m)")
        ax.set_xlabel("Date")
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        
        plt.tight_layout()
        plt.savefig(REPORTS_DIR / "volume_trends.png", dpi=150, bbox_inches="tight")
        plt.close()
        print(f"✓ reports/volume_trends.png")

        # Exercise distribution
        exercise_stats = defaultdict(lambda: {"load": 0})
        for s in sets:
            exercise_stats[s["exercise"]]["load"] += s["load"]
        sorted_ex = sorted(exercise_stats.items(), key=lambda x: x[1]["load"], reverse=True)[:10]
        fig, ax = plt.subplots(figsize=(12, 6))
        exercises = [ex for ex, _ in sorted_ex][::-1]
        volumes = [stats["load"] for _, stats in sorted_ex][::-1]
        ax.barh(exercises, volumes, color="steelblue")
        ax.set_title("Top 10 Exercises by Volume", fontsize=12, fontweight="bold")
        ax.set_xlabel("Total Volume (kg·m)")
        ax.grid(True, alpha=0.3, axis="x")
        plt.tight_layout()
        plt.savefig(REPORTS_DIR / "exercise_distribution.png", dpi=150, bbox_inches="tight")
        plt.close()
        print(f"✓ reports/exercise_distribution.png")

        print(f"\nDone. Reports saved to: {REPORTS_DIR}")


if __name__ == '__main__':
    m = Main()

#FILES
# main data : exercises,setss
# measures : bodyweight + the rest
# program instances
# status (current workout, current program, current exercise , current weight)

# SCRIPTS
# __main__, workout, interactive, stats, bv_utils, programs
