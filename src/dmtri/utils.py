import os
import sys
import shutil
from datetime import datetime, timezone
from pathlib import Path
import tomllib

KNOWN_DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
]

def parse_date_string(date_str: str, end: bool = False) -> str:
    for fmt in KNOWN_DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str, fmt)
            if end and dt.hour == 0 and dt.minute == 0 and dt.second == 0:
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt.isoformat()
        except ValueError:
            continue
    raise ValueError(f"Invalid date: '{date_str}'. Accepted formats: YYYY-MM-DD or ISO 8601.")

def get_version():
    root = Path(__file__).resolve().parents[2]
    pyproject_path = root / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
        return data["project"]["version"]

def is_all_star(values):
    return all(v == "*" for v in values)

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

def check_wildcard_constraints(args):
    if is_all_star(args.network) and is_all_star(args.station):
        print("Error: You cannot use '*' for both --network and --station.", file=sys.stderr)
        sys.exit(1)

def maybe_copy_config(args):
    if not args.config:
        return
    user_config = Path(args.config)
    default_config_path = Path.home() / ".config" / "datacenter-change-trigger" / "config.toml"
    try:
        if not default_config_path.exists() or user_config.resolve() != default_config_path.resolve():
            default_config_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(user_config, default_config_path)
            print(f"Config saved to {default_config_path}")
    except Exception as e:
        print(f"Warning: Failed to save config file: {e}", file=sys.stderr)

def validate_datetime_range(start_dt, end_dt):
    now = datetime.now(timezone.utc)


    if start_dt > now:
        print("Error: --starttime cannot be in the future.", file=sys.stderr)
        sys.exit(1)

    if end_dt > now:
        print("Error: --endtime cannot be in the future.", file=sys.stderr)
        sys.exit(1)

    if end_dt <= start_dt:
        print("Error: --endtime must be after --starttime.", file=sys.stderr)
        sys.exit(1)

    duration_days = (end_dt - start_dt).days
    if duration_days > 7:
        print(f"Warning: You are querying more than 7 days of data ({duration_days} days).")
        proceed = input("Are you sure you want to continue? (y/N): ").strip().lower()
        if proceed != "y":
            print("Aborted by user.")
            sys.exit(0)

def parse_datetime_args(args):
    try:
        start_dt = datetime.fromisoformat(args.starttime)
        end_dt = datetime.fromisoformat(args.endtime)

        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)

        return start_dt, end_dt

    except ValueError:
        print("Error: Invalid date format. Use ISO 8601 (e.g. 2025-01-01T00:00:00)", file=sys.stderr)
        sys.exit(1)

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
    check_wildcard_constraints(args)
    maybe_copy_config(args)

    start_dt, end_dt = parse_datetime_args(args)
    validate_datetime_range(start_dt, end_dt)
    types = validate_types(args)

    return start_dt, end_dt, types
