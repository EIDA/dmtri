import ansible_runner
import sys
from pathlib import Path
import logging
from dmtri.paths import INVENTORY_FILE


logger = logging.getLogger(__name__)
def run_hook(playbook_name: Path, vars: dict,inventory: Path = INVENTORY_FILE) -> None:
    """
    Run an Ansible playbook using ansible_runner.run_command, bypassing the project layout.
    """

    # Build the extra vars string manually
    extra_vars = []
    for key, value in vars.items():
        if isinstance(value, list):
            value = ",".join(value)
        extra_vars.extend(["-e", f"{key}='{value}'"])

    cmd = [
        "ansible-playbook",
        str(playbook_name.resolve()),
        "-i",
        str(inventory.resolve()),
        
    ] + extra_vars


    logger.info(f"Running: {' '.join(str(x) for x in cmd)}")


    out, err, rc = ansible_runner.run_command(
        executable_cmd="ansible-playbook",
        cmdline_args=cmd[1:], 
        input_fd=sys.stdin,
        output_fd=sys.stdout,
        error_fd=sys.stderr,
    )

    if rc != 0:
        logger.error(f"Playbook {playbook_name} failed with return code {rc}")
        sys.exit(rc)
    
    logger.info(f"Playbook {playbook_name} completed successfully")
