import argparse, sys
import bv_utils,stats,workout,interactive


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
        #if not hasattr(self, args.command):
        #    print('Unrecognized command')
        #    parser.print_help()
            #exit(1)
        # use dispatch pattern to invoke method with same name
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


if __name__ == '__main__':
    m = Main()

#FILES
# main data : exercises,setss
# measures : bodyweight + the rest
# program instances
# status (current workout, current program, current exercise , current weight)

# SCRIPTS
# __main__, workout, interactive, stats, bv_utils, programs
