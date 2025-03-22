import argparse
import sys
from datetime import datetime
from datacenter_change_trigger import nodes, query

VERSION = "0.1.0"
PROJECT_URL = "https://github.com/EIDA/datacenter-change-trigger"

def main():
    parser = argparse.ArgumentParser(
        description="Trigger data/metadata refresh across EIDA datacenters"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}\n{PROJECT_URL}")
    parser.add_argument("--reload-nodes", action="store_true", help="Refresh and cache the list of EIDA nodes")

    subparsers = parser.add_subparsers(dest="command")

    # Shared options for 'refresh' and 'clean'
    shared = argparse.ArgumentParser(add_help=False)

    shared.add_argument("-n", "--network", nargs="+", default=["*"],
                        help="FDSN network code(s), supports wildcards")
    shared.add_argument("-s", "--station", nargs="+", default=["*"],
                        help="FDSN station code(s), supports wildcards")
    shared.add_argument("-l", "--location", nargs="+", default=["*"],
                        help="FDSN location code(s), supports wildcards")
    shared.add_argument("-c", "--channel", nargs="+", default=["*"],
                        help="FDSN channel code(s), supports wildcards")
    shared.add_argument("-S", "--starttime", required=True,
                        help="Start time")
    shared.add_argument("-E", "--endtime", default=datetime.utcnow().isoformat(),
                        help="End time, default: now)")
    shared.add_argument("--type", default="data,metadata",
                        help="Comma-separated types to process (data, metadata)")

    # Commands
    subparsers.add_parser("refresh", parents=[shared], help="Refresh data/metadata")
    subparsers.add_parser("clean", parents=[shared], help="Clean outdated data/metadata")

    args = parser.parse_args()

    # Handle standalone --reload-nodes
    if args.reload_nodes and args.command is None:
        print("Refreshing node cache from routing service...")
        fetched = nodes.fetch_nodes_from_api()
        if fetched:
            print(f"Fetched and cached {len(fetched)} nodes.")
        else:
            print("Failed to fetch nodes. Cache not updated.")
        return

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Validate network/station constraint
    if args.network == ["*"] and args.station == ["*"]:
        print("Error: You must specify at least --network or --station (not both '*').", file=sys.stderr)
        sys.exit(1)

    # Load or reload nodes
    if args.reload_nodes:
        print("Reloading node list from routing service...")
        node_list = nodes.fetch_nodes_from_api()
        if not node_list:
            print("Failed to reload nodes. Using default node list.")
            node_list = nodes.DEFAULT_NODES
    else:
        node_list = nodes.load_nodes()

    # Parse and validate times
    try:
        start_dt = datetime.fromisoformat(args.starttime)
        end_dt = datetime.fromisoformat(args.endtime)
    except ValueError:
        print("Error: Invalid date format. Use ISO format (e.g. 2025-01-01T00:00:00)", file=sys.stderr)
        sys.exit(1)

    duration_days = (end_dt - start_dt).days
    if duration_days > 7:
        print(f"Warning: You are querying more than 7 days of data ({duration_days} days).")
        proceed = input("Are you sure you want to continue? (y/N): ").strip().lower()
        if proceed != "y":
            print("Aborted by user.")
            sys.exit(0)

    # Parse type
    types = [t.strip() for t in args.type.split(",") if t.strip() in ("data", "metadata")]
    if not types:
        print("Error: --type must contain at least one of 'data' or 'metadata'", file=sys.stderr)
        sys.exit(1)

    # Build query parameters
    query_params = {
        "network": args.network,
        "station": args.station,
        "location": args.location,
        "channel": args.channel,
        "starttime": args.starttime,
        "endtime": args.endtime,
        "type": types,
    }

    # Run query
    result = query.query_all_nodes_parallel(node_list, query_params)

    if result:
        full_url, base_url, data = result
        print(f"\nFound data from: {base_url}")
        print(f"Query URL: {full_url}")
        #print(f"\n{data}")
    else:
        print("\nNo node returned valid metadata for the given parameters.")
        sys.exit(1)
