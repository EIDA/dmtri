from pathlib import Path
import appdirs
import os

MODULE_DIR = Path(__file__).resolve().parent
DATA_DIR = MODULE_DIR / "data"

# Bundled directories (always available)
PLAYBOOKS_DIR = DATA_DIR / "playbooks"
INVENTORY_DIR = DATA_DIR / "inventory"

# User config directory (populated by `dmtri init`)
USER_CONFIG_DIR = Path(appdirs.user_config_dir("dmtri"))
USER_PLAYBOOKS_DIR = USER_CONFIG_DIR / "playbooks"

# Ansible config files (always bundled)
ANSIBLE_QUIET_CFG = DATA_DIR / "ansible_quiet.cfg"
ANSIBLE_TRACK_CFG = DATA_DIR / "ansible_track.cfg"
ANSIBLE_VERBOSE_CFG = DATA_DIR / "ansible_verbose.cfg"

# Bundled inventory example (committed to git, safe to ship)
INVENTORY_EXAMPLE = INVENTORY_DIR / "hosts.ini.example"
# Local inventory — git-ignored, never bundled in the package, used for repo dev
INVENTORY_FILE = INVENTORY_DIR / "hosts.ini"


def get_inventory_path(override=None):
    """
    Determine the inventory path using the following priority:
    1. CLI flag (--inventory)
    2. Environment variable (DMTRI_INVENTORY)
    3. User config directory (~/.config/dmtri/hosts.ini)

    Raises SystemExit with a helpful message if no inventory is found.
    Run `dmtri init` to create your local hosts.ini from the example.
    """
    import sys
    if override:
        p = Path(override).resolve()
        if not p.exists():
            print(f"Error: inventory file not found: {p}", file=sys.stderr)
            sys.exit(1)
        return p

    env_val = os.environ.get("DMTRI_INVENTORY")
    if env_val:
        p = Path(env_val).resolve()
        if not p.exists():
            print(f"Error: DMTRI_INVENTORY points to a missing file: {p}", file=sys.stderr)
            sys.exit(1)
        return p

    user_path = USER_CONFIG_DIR / "hosts.ini"
    if user_path.exists():
        return user_path

    # Local dev fallback: repo clone with a git-ignored hosts.ini
    if INVENTORY_FILE.exists():
        return INVENTORY_FILE

    print(
        "Error: No inventory file found.\n"
        "Run \"dmtri init\" to create your local hosts.ini from the bundled example,\n"
        f"then edit it at: {USER_CONFIG_DIR / 'hosts.ini'}",
        file=sys.stderr,
    )
    sys.exit(1)


def _resolve_playbook(relative_path: str) -> Path:
    """
    Return user playbook if it exists, otherwise fall back to bundled version.
    relative_path is relative to the playbooks root, e.g. 'refresh/seedpsd_refresh.yml'
    """
    user_pb = USER_PLAYBOOKS_DIR / relative_path
    if user_pb.exists():
        return user_pb
    return PLAYBOOKS_DIR / relative_path


# Playbooks — resolved dynamically so user overrides are respected
PLAYBOOK_TRACK = _resolve_playbook("track.yml")

PLAYBOOK_SEEDPSD_REFRESH   = _resolve_playbook("refresh/seedpsd_refresh.yml")
PLAYBOOK_WFCATALOG_REFRESH = _resolve_playbook("refresh/wfcatalog_refresh.yml")
PLAYBOOK_AVAILABILITY_REFRESH = _resolve_playbook("refresh/availability_refresh.yml")
PLAYBOOK_METADATA_REFRESH  = _resolve_playbook("refresh/seedpsd_metadata_refresh.yml")

# Consistency-repair (dmtri fix): reuses wfcatalog_refresh, plus a scoped
# availability rebuild (docker exec avail-rebuild) instead of the global restart.
PLAYBOOK_AVAILABILITY_REBUILD = _resolve_playbook("fix/availability_rebuild.yml")

PLAYBOOK_SEEDPSD_CLEAN      = _resolve_playbook("clean/seedpsd_clean.yml")
PLAYBOOK_WFCATALOG_CLEAN    = _resolve_playbook("clean/wfcatalog_clean.yml")
PLAYBOOK_AVAILABILITY_CLEAN = _resolve_playbook("clean/availability_clean.yml")

# Group playbooks by command
COMMAND_PLAYBOOKS = {
    "refresh": {
        "data": [
            PLAYBOOK_SEEDPSD_REFRESH,
            PLAYBOOK_WFCATALOG_REFRESH,
            PLAYBOOK_AVAILABILITY_REFRESH,
        ],
        "metadata": [
            PLAYBOOK_METADATA_REFRESH,
        ]
    },
    "clean": [
        PLAYBOOK_SEEDPSD_CLEAN,
        PLAYBOOK_WFCATALOG_CLEAN,
        PLAYBOOK_AVAILABILITY_CLEAN,
    ],
    "track": [
        PLAYBOOK_TRACK
    ]
}
