import sys
import yaml
from pathlib import Path


def get_playbook_metadata(playbook_path: str):
    try:
        with open(playbook_path) as f:
            playbook = yaml.safe_load(f)

        if not playbook or not isinstance(playbook, list) or not playbook[0]:
            return {"error": "Empty playbook"}

        metadata = {
            "hosts": playbook[0].get("hosts", "unknown"),
            "description": playbook[0].get("vars", {}).get("description", ""),
            "tasks": []
        }

        for task in playbook[0].get("tasks", []):
            desc = task.get("vars", {}).get("description", task.get("name", "Unnamed Task"))
            metadata["tasks"].append(desc)

        return metadata

    except Exception as e:
        return {"error": str(e)}



    

def print_execution_plan(command: str, variables: dict, playbook_path: str, metadata=None):
    if metadata is None:
        metadata = get_playbook_metadata(playbook_path)

    print("\nExecution Plan")
    print("-" * 40)
    print(f"Command     : {command}")
    print(f"Playbook    : {playbook_path}")

    if "error" in metadata:
        print(f"Warning     : {metadata['error']}")
    else:
        print(f"Hosts       : {metadata['hosts']}")
        print(f"Description : {metadata['description']}")
        print("Steps       :")
        for idx, desc in enumerate(metadata['tasks'], start=1):
            print(f"  {idx}. {desc}")

    if variables:
        print("\nVariables:")
        for k, v in variables.items():
            print(f"  {k:10}: {v}")

    confirm = input("\nProceed with this execution plan? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Aborted by user.")
        sys.exit(0)