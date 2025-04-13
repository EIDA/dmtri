import ansible_runner
import sys
from pathlib import Path


def run_hook(playbook_name: str, vars: dict, runner_dir: str = "playbooks") -> None:
    """
    Run the given Ansible playbook using ansible-runner with provided variables.

    Args:
        playbook_name (str): The name or path of the playbook (relative to runner_dir).
        vars (dict): Variables to pass to the playbook.
        runner_dir (str): Directory containing the playbook (default: "playbooks").

    Raises:
        FileNotFoundError: If the playbook does not exist.
        SystemExit: If the Ansible run fails.
    """
    playbook_path = Path(runner_dir) / playbook_name
    if not playbook_path.exists():
        raise FileNotFoundError(f"Playbook not found: {playbook_path.resolve()}")

    print(f" Running playbook: {playbook_path}")

    result = ansible_runner.run(
        private_data_dir=runner_dir,
        playbook=playbook_name,
        extravars=vars,
        quiet=False,
    )

    if result.rc != 0 or result.status == "failed":
        print(f" Playbook {playbook_name} failed (rc={result.rc})", file=sys.stderr)
        sys.exit(1)

    print(f"Playbook {playbook_name} completed successfully")
