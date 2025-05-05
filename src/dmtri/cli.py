import argparse
import sys
from datetime import datetime, timezone
import logging

from dmtri.execution_plan import print_execution_plan
from dmtri.utils import get_version, validate_and_normalize_args
from dmtri.hooks.hooks import run_hook
from dmtri.paths import COMMAND_PLAYBOOKS

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

PROJECT_URL = "https://github.com/EIDA/dmtri/issues"


def main():
    global_options = argparse.ArgumentParser(add_help=False)

    parser = argparse.ArgumentParser(
        description="Trigger data/metadata refresh or cleaning for multiple EIDA endpoints.",
        parents=[global_options]
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s version {get_version()} — See {PROJECT_URL} for updates or to report issues."
    )

    subparsers = parser.add_subparsers(dest="command")

    shared = argparse.ArgumentParser(add_help=False, parents=[global_options])
    shared.add_argument("-n", "--network", nargs="+", default=["*"], help="FDSN network code(s), supports wildcards")
    shared.add_argument("-s", "--station", nargs="+", default=["*"], help="FDSN station code(s), supports wildcards")
    shared.add_argument("-l", "--location", nargs="+", default=["*"], help="FDSN location code(s), supports wildcards")
    shared.add_argument("-c", "--channel", nargs="+", default=["*"], help="FDSN channel code(s), supports wildcards")
    shared.add_argument("-S", "--starttime", required=True, help="Start time (ISO 8601 format)")

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    shared.add_argument("-E", "--endtime", default=now_str, help="End time (default: now in UTC)")
    shared.add_argument("--type", default="data,metadata", help="Comma-separated types to process (data, metadata)")
    shared.add_argument("--no-confirm", action="store_true", help="Skip confirmation prompt before executing")

    subparsers.add_parser("refresh", parents=[shared], help="Refresh data/metadata using configured playbooks.")
    subparsers.add_parser("clean", parents=[shared], help="Clean outdated data/metadata using configured playbooks.")

    doctor_parser = subparsers.add_parser("doctor", help="Check SSH connectivity to all inventory hosts")
    doctor_parser.add_argument("-v", "--verbose", action="store_true", help="Show full Ansible output per host")

    args = parser.parse_args()

    if args.command == "doctor":
        from dmtri.doctor import run_diagnostics
        return run_diagnostics(verbose=args.verbose)

    elif args.command in ("refresh", "clean"):
        start_dt, end_dt, types = validate_and_normalize_args(args, parser)

        vars_to_pass = {
            "network": args.network,
            "station": args.station,
            "location": args.location,
            "channel": args.channel,
            "starttime": args.starttime,
            "endtime": args.endtime,
            "type": [t.strip() for t in args.type.split(",")],
        }

        playbooks = COMMAND_PLAYBOOKS.get(args.command, [])
        if not playbooks:
            print(f"No playbooks configured for command '{args.command}'.")
            sys.exit(1)

        if not args.no_confirm:
            for pb in playbooks:
                print_execution_plan(args.command, vars_to_pass, pb)
            proceed = input("\nDo you want to proceed with executing all playbooks? (y/N): ").strip().lower()
            if proceed != "y":
                print("Aborted by user.")
                sys.exit(0)

        for pb in playbooks:
            run_hook(pb, vars_to_pass)

    else:
        parser.print_help()
        sys.exit(1)
