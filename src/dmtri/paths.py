from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
SRC_DIR = MODULE_DIR.parent

# Directories
PLAYBOOKS_DIR = SRC_DIR / "playbooks"
INVENTORY_DIR = SRC_DIR / "inventory"

# Inventory file
INVENTORY_FILE = INVENTORY_DIR / "hosts.ini"

# Specific playbooks
PLAYBOOK_TRACK = PLAYBOOKS_DIR / "track.yml"
PLAYBOOK_LIST_SDS = PLAYBOOKS_DIR / "list_sds_files.yml"

# Refresh Data playbooks
PLAYBOOK_SEEDPSD_REFRESH = PLAYBOOKS_DIR / "refresh" / "seedpsd_refresh.yml"
PLAYBOOK_WFCATALOG_REFRESH = PLAYBOOKS_DIR / "refresh" / "wfcatalog_refresh.yml"
PLAYBOOK_AVAILABILITY_REFRESH = PLAYBOOKS_DIR / "refresh" / "availability_refresh.yml"
# Refresh metadata playbooks
PLAYBOOK_METADATA_REFRESH = PLAYBOOKS_DIR / "refresh" / "seedpsd_metadata_refresh.yml"

# Clean playbooks
PLAYBOOK_SEEDPSD_CLEAN = PLAYBOOKS_DIR / "clean" /"seedpsd_clean.yml"
PLAYBOOK_WFCATALOG_CLEAN = PLAYBOOKS_DIR / "clean" / "wfcatalog_clean.yml"
PLAYBOOK_AVAILABILITY_CLEAN = PLAYBOOKS_DIR / "clean" / "availability_clean.yml"

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
