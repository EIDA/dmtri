import argparse
import sys
import os
from datetime import datetime, timezone
import logging

from dmtri.execution_plan import print_execution_plan
from dmtri.utils import get_version, validate_and_normalize_args , parse_flexible_date
from dmtri.hooks.hooks import run_hook
from dmtri.paths import COMMAND_PLAYBOOKS, ANSIBLE_QUIET_CFG, ANSIBLE_TRACK_CFG, ANSIBLE_VERBOSE_CFG, get_inventory_path

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
    parser.add_argument("-i", "--inventory", help="Path to custom Ansible inventory file")

    subparsers = parser.add_subparsers(dest="command")

    shared = argparse.ArgumentParser(add_help=False, parents=[global_options])
    shared.add_argument("-n", "--network", nargs="+", default=["*"], help="FDSN network code(s), supports wildcards")
    shared.add_argument("-s", "--station", nargs="+", default=["*"], help="FDSN station code(s), supports wildcards")
    shared.add_argument("-l", "--location", nargs="+", default=["*"], help="FDSN location code(s), supports wildcards")
    shared.add_argument("-c", "--channel", nargs="+", default=["*"], help="FDSN channel code(s), supports wildcards")
    shared.add_argument(
        "-S", "--starttime", "--start",
        type=parse_flexible_date,
        required=True,
        help="Start time (e.g. '2025-07-01', '2025-07-01T12:00:00', 'yesterday', '-2d')",
    )
    shared.add_argument(
        "-E", "--endtime", "--end",
        type=parse_flexible_date,
        default="now",
        help="End time (default: now in UTC)",
    )
    shared.add_argument("--type", default="data,metadata", help="Comma-separated types to process (data, metadata)")
    shared.add_argument("--no-confirm", action="store_true", help="Skip confirmation prompt before executing")
    shared.add_argument("--debug", action="store_true", help="Show verbose output from Ansible")

    subparsers.add_parser("refresh", parents=[shared], help="Refresh data/metadata using configured playbooks.")
    subparsers.add_parser("clean", parents=[shared], help="(not yet implemented) Clean outdated data/metadata.")

    fix_parser = subparsers.add_parser("fix", help="Automatically repair inconsistencies from an eida-consistency report.")
    fix_parser.add_argument("report", help="Consistency report: URL or local JSON path")
    fix_parser.add_argument("--verify-only", action="store_true", help="Only re-check status (no rebuilding)")
    fix_parser.add_argument("--days", type=int, default=None, help="Max days to explore boundaries (passthrough to eida-consistency)")
    fix_parser.add_argument("--index", type=int, action="append", dest="index", help="Restrict to specific report index(es); repeatable")
    fix_parser.add_argument("--no-confirm", action="store_true", help="Skip confirmation prompt before executing")
    fix_parser.add_argument("-v", "--verbose", action="store_true", help="Stream eida-consistency explore progress (per-query URLs) live instead of waiting silently")
    fix_parser.add_argument("--debug", action="store_true", help="Show verbose output from Ansible")
    fix_parser.add_argument("--psd", action="store_true",
                            help="Also repair 'data present, no PSD' findings (reads them from the report; "
                                 "can take minutes per finding, so it is opt-in)")
    fix_parser.add_argument("--psd-only", action="store_true",
                            help="Repair only PSD findings, skipping the availability chain")
    fix_parser.add_argument("--psd-window", type=int, default=None, metavar="N",
                            help="Days either side of a PSD finding to recompute (default 15)")
    fix_parser.add_argument("--required-only", action="store_true",
                            help="With --psd: repair only findings where PSD is an obligation (day >= 2024-01-01)")
    subparsers.add_parser("track", help="Track job status via tracking playbook.")
    doctor_parser = subparsers.add_parser("doctor", help="Check SSH connectivity to all inventory hosts")
    doctor_parser.add_argument("-v", "--verbose", action="store_true", help="Show full Ansible output per host")

    init_parser = subparsers.add_parser("init", help="Scaffold user config directory with bundled playbooks and inventory")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing user config files")

    args = parser.parse_args()

    # `init` scaffolds the config (including the inventory), so it must run
    # before any inventory resolution — otherwise a brand-new user can never
    # bootstrap, since get_inventory_path() exits when no inventory exists.
    if args.command == "init":
        from dmtri.init import run_init
        return run_init(force=args.force)

    if args.command == "track":
        cfg_path = ANSIBLE_TRACK_CFG
    else:
        cfg_path = ANSIBLE_VERBOSE_CFG if getattr(args, "debug", False) else ANSIBLE_QUIET_CFG

    os.environ["ANSIBLE_CONFIG"] = str(cfg_path.resolve())
    inventory_path = get_inventory_path(args.inventory)

    if args.command == "doctor":
        from dmtri.doctor import run_diagnostics
        return run_diagnostics(verbose=args.verbose, inventory=inventory_path)

    elif args.command == "clean":
        # `clean` is intentionally deferred: its playbooks are not yet
        # implemented. Fail clearly instead of running empty playbooks.
        print(
            "`dmtri clean` is not yet implemented and is planned for a future release.",
            file=sys.stderr,
        )
        sys.exit(2)

    elif args.command == "refresh":
        start_dt, end_dt, types = validate_and_normalize_args(args, parser)

        vars_to_pass = {
            "network": args.network,
            "station": args.station,
            "location": args.location,
            "channel": args.channel,
            "starttime": args.starttime.isoformat(),
            "endtime": args.endtime.isoformat(),
            "type": [t.strip() for t in args.type.split(",")],
            "debug": args.debug,
        }

        selected_types = vars_to_pass["type"]
        valid_types = set(COMMAND_PLAYBOOKS["refresh"].keys())

        invalid = set(selected_types) - valid_types
        if invalid:
            print(f" Invalid --type: {', '.join(invalid)}. Valid types are: {', '.join(valid_types)}.")
            sys.exit(1)

        playbooks = []
        for t in selected_types:
            playbooks.extend(COMMAND_PLAYBOOKS["refresh"][t])

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
            run_hook(pb, vars_to_pass, inventory=inventory_path)

    elif args.command == "fix":
        from dmtri.fix import run_fix, run_verify_only, run_psd_fix, DEFAULT_PSD_WINDOW_DAYS
        try:
            if args.verify_only:
                rc = run_verify_only(args.report, inventory=inventory_path,
                                     days=args.days, indices=args.index, verbose=args.verbose)
            else:
                rc = 0
                # Availability first: fast, and proven. PSD is the expensive half.
                if not args.psd_only:
                    rc = run_fix(args.report, inventory=inventory_path, days=args.days,
                                 indices=args.index, no_confirm=args.no_confirm,
                                 debug=args.debug, verbose=args.verbose)
                if args.psd or args.psd_only:
                    psd_rc = run_psd_fix(
                        args.report, inventory=inventory_path,
                        window_days=(DEFAULT_PSD_WINDOW_DAYS if args.psd_window is None
                                     else args.psd_window),
                        required_only=args.required_only, no_confirm=args.no_confirm)
                    rc = rc or psd_rc
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(2)
        sys.exit(rc)

    elif args.command == "track":
        playbooks = COMMAND_PLAYBOOKS.get("track", [])
        if not playbooks:
            print("No playbooks configured for command 'track'.")
            sys.exit(1)
        for pb in playbooks:
            run_hook(pb, {}, inventory=inventory_path)

    else:
        parser.print_help()
        sys.exit(1)
