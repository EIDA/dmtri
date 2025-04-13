import yaml

def get_playbook_metadata(playbook_path: str) -> dict:
    """
    Load metadata from an Ansible playbook.
    Expects `vars.description` or other top-level info.
    """
    try:
        with open(playbook_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, list) or not data:
            return {}

        play = data[0]  # only read first play
        meta = {
            "hosts": play.get("hosts", "unspecified"),
            "tasks": len(play.get("tasks", [])),
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
        print(f"⚠️  Warning  : {metadata['error']}")
    else:
        print(f"Hosts       : {metadata['hosts']}")
        print(f"Tasks       : {metadata['tasks']}")
        print(f"Description : {metadata['description']}")

    print("\nVariables:")
    for k, v in variables.items():
        print(f"  {k:10}: {v}")

    confirm = input("\nThis is what I plan to do. OK for you? [y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted by user.")
        sys.exit(0)
