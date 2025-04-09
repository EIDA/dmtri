import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from dmtri.utils import (
    get_version,
    validate_and_normalize_args
)
from dmtri import query
from dmtri.config import load_config

PROJECT_URL = "https://github.com/EIDA/dmtri/issues"

def main():
    global_options = argparse.ArgumentParser(add_help=False)
    global_options.add_argument("--config", help="Path to custom configuration file")

    parser = argparse.ArgumentParser(
        description="Trigger data/metadata refresh for multiple EIDA endpoints",
        parents=[global_options]
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s version {get_version()} — See {PROJECT_URL} for updates or to report issues."
    )

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

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    shared.add_argument("-E", "--endtime", default=now_str,
                        help="End time (default: now in UTC, formatted without timezone)")
    shared.add_argument("--type", default="data,metadata",
                        help="Comma-separated types to process (data, metadata)")

    subparsers.add_parser("refresh", parents=[shared], help="Refresh data/metadata")
    subparsers.add_parser("clean", parents=[shared], help="Clean outdated data/metadata")

    args = parser.parse_args()

    
    start_dt, end_dt, types = validate_and_normalize_args(args, parser)

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
        "starttime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "endtime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "type": types,
        "format": "xml",
        "level": "response",
    }

    result = query.query_all_nodes_parallel(endpoints, query_params)

    if result:
        full_url, base_url, _ = result
        print(f"\nValid response from: {base_url}")
        print(f"Query URL: {full_url}")
    else:
        print("\nNo valid metadata found at any configured FDSN endpoint.")
        sys.exit(1)
