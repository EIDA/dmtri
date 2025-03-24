import argparse
import sys
from datetime import datetime
from pathlib import Path
import shutil

from datacenter_change_trigger import query
from datacenter_change_trigger.config import load_config

VERSION = "0.1.0"
PROJECT_URL = "https://github.com/EIDA/datacenter-change-trigger"

def main():
    global_options = argparse.ArgumentParser(add_help=False)
    global_options.add_argument("--config", help="Path to custom configuration file")

    parser = argparse.ArgumentParser(
        description="Trigger data/metadata refresh for multiple EIDA endpoints",
        parents=[global_options]
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}\n{PROJECT_URL}")
    subparsers = parser.add_subparsers(dest="command")

    shared = argparse.ArgumentParser(add_help=False, parents=[global_options])

    shared.add_argument("-n", "--network", nargs="+", default=["*"],
                        help="FDSN network code(s), supports wildcards")
    shared.add_argument("-s", "--station", nargs="+", default=["*"],
                        help="FDSN station code(s), supports wildcards")
    shared.add_argument("-l", "--location", nargs="+", default=["*"],
                        help="FDSN location code(s), supports wildcards")
    shared.add_argument("-c", "--channel", nargs="+", default=["*"],
                        help="FDSN channel code(s), supports wildcards")
    shared.add_argument("-S", "--starttime", required=True,
                        help="Start time (ISO 8601 format)")
    shared.add_argument("-E", "--endtime", default=datetime.utcnow().isoformat(),
                        help="End time (default: now)")
    shared.add_argument("--type", default="data,metadata",
                        help="Comma-separated types to process (data, metadata)")

    subparsers.add_parser("refresh", parents=[shared], help="Refresh data/metadata")
    subparsers.add_parser("clean", parents=[shared], help="Clean outdated data/metadata")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Save provided config to default location
    if args.config:
        user_config = Path(args.config)
        default_config_path = Path.home() / ".config" / "datacenter-change-trigger" / "config.toml"
        try:
            if not default_config_path.exists() or user_config.resolve() != default_config_path.resolve():
                default_config_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(user_config, default_config_path)
                print(f"Config saved to {default_config_path}")
        except Exception as e:
            print(f"Warning: Failed to save config file: {e}", file=sys.stderr)

    if args.network == ["*"] and args.station == ["*"]:
        print("Error: You must specify at least --network or --station (not both '*').", file=sys.stderr)
        sys.exit(1)

    try:
        start_dt = datetime.fromisoformat(args.starttime)
        end_dt = datetime.fromisoformat(args.endtime)
    except ValueError:
        print("Error: Invalid date format. Use ISO 8601 (e.g. 2025-01-01T00:00:00)", file=sys.stderr)
        sys.exit(1)

    duration_days = (end_dt - start_dt).days
    if duration_days > 7:
        print(f"Warning: You are querying more than 7 days of data ({duration_days} days).")
        proceed = input("Are you sure you want to continue? (y/N): ").strip().lower()
        if proceed != "y":
            print("Aborted by user.")
            sys.exit(0)

    types = [t.strip() for t in args.type.split(",") if t.strip() in ("data", "metadata")]
    if not types:
        print("Error: --type must contain at least one of 'data' or 'metadata'", file=sys.stderr)
        sys.exit(1)

    try:
        config = load_config(args.config)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    endpoints = list(config["endpoints"].values())

    query_params = {
        "network": args.network,
        "station": args.station,
        "location": args.location,
        "channel": args.channel,
        "starttime": args.starttime,
        "endtime": args.endtime,
        "type": types,
    }

    result = query.query_all_nodes_parallel(endpoints, query_params)

    if result:
        full_url, base_url, _ = result
        print(f"\nValid response from: {base_url}")
        print(f"Query URL: {full_url}")
    else:
        print("\nNo valid metadata found at any configured FDSN endpoint.")
        sys.exit(1)
