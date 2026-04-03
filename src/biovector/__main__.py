import argparse, sys
import bv_utils,stats,workout,interactive
import datetime


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


if __name__ == '__main__':
    m = Main()

#FILES
# main data : exercises,setss
# measures : bodyweight + the rest
# program instances
# status (current workout, current program, current exercise , current weight)

# SCRIPTS
# __main__, workout, interactive, stats, bv_utils, programs
