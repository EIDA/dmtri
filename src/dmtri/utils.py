import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import tomllib

from importlib.metadata import version, PackageNotFoundError

def get_version():
    try:
        # Try to get version from installed package metadata
        return version("eida-dmtri")
    except PackageNotFoundError:
        # Fallback for local development where the package might not be installed
        try:
            root = Path(__file__).resolve().parents[2]
            pyproject_path = root / "pyproject.toml"
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                return data.get("project", {}).get("version", "unknown")
        except Exception:
            return "unknown"

def maybe_warn_shell_globbing(args):
    cwd_files = set(os.listdir("."))

    def looks_globbed(value_list):
        return any(v in cwd_files for v in value_list)

    if looks_globbed(args.station):
        print("⚠️  Error: --station appears to be expanded by your shell. Use --station '*'.", file=sys.stderr)
        sys.exit(1)

    if looks_globbed(args.network):
        print("⚠️  Error: --network appears to be expanded by your shell. Use --network '*'.", file=sys.stderr)
        sys.exit(1)

def validate_datetime_range(start_dt, end_dt):
    now = datetime.now(timezone.utc)


    if start_dt > now:
        print("Error: --starttime cannot be in the future.", file=sys.stderr)
        sys.exit(1)

    if end_dt > now:
        print("Error: --endtime cannot be in the future.", file=sys.stderr)
        sys.exit(1)

    if end_dt < start_dt:
        print("Error: --endtime must be on or after --starttime.", file=sys.stderr)
        sys.exit(1)

    duration_days = (end_dt - start_dt).days
    if duration_days > 7:
        print(f"Warning: You are querying more than 7 days of data ({duration_days} days).")
        proceed = input("Are you sure you want to continue? (y/N): ").strip().lower()
        if proceed != "y":
            print("Aborted by user.")
            sys.exit(0)
def parse_flexible_date(value: str) -> datetime:
    """Parses ISO 8601, partial date, or relative expressions like 'yesterday', '-1d', etc."""
    from datetime import timedelta
    import re

    value = value.strip().lower()
    now = datetime.now(timezone.utc)

    if value == "now":
        return now
    if value == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if value == "yesterday":
        return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Relative offsets: +1d, -2h, +30m
    match = re.fullmatch(r"([+-])(\d+)([dhms])", value)
    if match:
        sign, number, unit = match.groups()
        number = int(number)
        delta = {"d": timedelta(days=number), "h": timedelta(hours=number),
                 "m": timedelta(minutes=number), "s": timedelta(seconds=number)}[unit]
        return now + delta if sign == "+" else now - delta

    # Try parsing ISO 8601 or partial formats
    formats = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M")
    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except ValueError:
            continue

    raise ValueError(f"Invalid date format: '{value}'")

def parse_datetime_args(args):
    return args.starttime, args.endtime


def validate_types(args):
    types = [t.strip() for t in args.type.split(",") if t.strip() in ("data", "metadata")]
    if not types:
        print("Error: --type must contain at least one of 'data' or 'metadata'", file=sys.stderr)
        sys.exit(1)
    return types

def validate_and_normalize_args(args, parser):
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    maybe_warn_shell_globbing(args)
    start_dt, end_dt = parse_datetime_args(args)
    validate_datetime_range(start_dt, end_dt)
    types = validate_types(args)

    return start_dt, end_dt, types
