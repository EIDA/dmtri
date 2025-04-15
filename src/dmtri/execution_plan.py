import sys
import yaml
from pathlib import Path


def get_playbook_metadata(playbook_path: Path) -> dict:
    """
    Load metadata from an Ansible playbook.
    Extracts hosts, task names, and description (if defined in vars).
    """
    try:
        with open(playbook_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, list) or not data:
            return {"error": "Playbook is empty or malformed"}

        play = data[0]  # only read first play

        meta = {
            "hosts": play.get("hosts", "unspecified"),
            "tasks": [task.get("name", "Unnamed task") for task in play.get("tasks", [])],
            "description": play.get("vars", {}).get("description", "No description provided.")
        }

        return meta

    except Exception as e:
        return {"error": f"Failed to parse playbook: {e}"}


def print_execution_plan(command: str, variables: dict, playbook_path: str):
    metadata = get_playbook_metadata(playbook_path)

    print("\nExecution Plan")
    print("-" * 40)
    print(f"Command     : {command}")
    print(f"Playbook    : {playbook_path}")
    if "error" in metadata:
        print(f" Warning  : {metadata['error']}")
    else:
        print(f"Hosts       : {metadata['hosts']}")
        print(f"Tasks       : {metadata['tasks']}")
        print(f"Description : {metadata['description']}")

    print("\nVariables:")
    for k, v in variables.items():
        print(f"  {k:10}: {v}")

    confirm = input("\nProceed with this execution plan? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Aborted by user.")
        sys.exit(0)
