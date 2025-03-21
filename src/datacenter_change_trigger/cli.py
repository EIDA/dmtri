import argparse
import sys
from datetime import datetime
from datacenter_change_trigger import query

VERSION = "0.1.0"
PROJECT_URL = "https://github.com/EIDA/datacenter-change-trigger"

def main():
    parser = argparse.ArgumentParser(
        description="Trigger data/metadata updates in EIDA datacenters."
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {VERSION}\n{PROJECT_URL}"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Common parser for refresh and clean
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("-n", "--network", nargs="+", default=["*"])
    common_parser.add_argument("-s", "--station", nargs="+", default=["*"])
    common_parser.add_argument("-l", "--location", nargs="+", default=["*"])
    common_parser.add_argument("-c", "--channel", nargs="+", default=["*"])
    common_parser.add_argument(
        "-S", "--starttime", required=True, help="Start time (e.g. 2025-01-01T00:00:00)"
    )
    common_parser.add_argument(
        "-E", "--endtime", default=datetime.utcnow().isoformat(),
        help="End time (default: now)"
    )
    common_parser.add_argument(
        "--type", default="data,metadata", help="Comma-separated types (default: data,metadata)"
    )

    subparsers.add_parser("refresh", parents=[common_parser], help="Refresh data/metadata")
    subparsers.add_parser("clean", parents=[common_parser], help="Clean outdated data")

    args = parser.parse_args()

    # Validation: At least network or station should be defined
    if args.network == ["*"] and args.station == ["*"]:
        print("Error: At least --network or --station must be defined.", file=sys.stderr)
        sys.exit(1)

    print(f"Running command: {args.command}")
    print(f"Networks: {args.network}")
    print(f"Stations: {args.station}")
    print(f"Start: {args.starttime}")
    print(f"End: {args.endtime}")
    print(f"Type: {args.type}")

    # Placeholder: Query metadata and trigger hooks (future logic)
    query_url = query.build_query_url(
        network=args.network,
        station=args.station,
        location=args.location,
        channel=args.channel,
        starttime=args.starttime,
        endtime=args.endtime
    )
    print(f"Query URL: {query_url}")

if __name__ == "__main__":
    main()
