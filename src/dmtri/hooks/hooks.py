import ansible_runner
import shutil
import sys
from pathlib import Path
import logging
from dmtri.paths import INVENTORY_FILE


logger = logging.getLogger(__name__)

# Exit code shells use for "command not found"; reported per play so a batch
# keeps its own accounting instead of dying with a traceback.
_RC_NOT_FOUND = 127


def _ansible_playbook() -> str:
    """Absolute path to ansible-playbook, preferring the one installed beside us.

    dmtri is usually launched as `.venv/bin/dmtri`, and a shebang sets the
    interpreter but NOT PATH -- so a bare "ansible-playbook" raises
    FileNotFoundError and every play dies before it starts. ansible is a
    declared dependency, so the console script sits next to this interpreter.
    """
    local = Path(sys.executable).parent / "ansible-playbook"
    if local.is_file():
        return str(local)
    return shutil.which("ansible-playbook") or ""
def run_hook(playbook_name: Path, vars: dict, inventory: Path = INVENTORY_FILE,
             exit_on_error: bool = True) -> int:
    """
    Run an Ansible playbook using ansible_runner.run_command, bypassing the project layout.

    Returns the playbook return code. By default (exit_on_error=True) it preserves
    the historical behavior of refresh/clean — sys.exit(rc) on failure. Callers that
    orchestrate a multi-step batch (e.g. `dmtri fix`) pass exit_on_error=False so one
    failed stream does not abort the whole run; they inspect the returned rc instead.
    """

    # Build the extra vars string manually
    extra_vars = []
    for key, value in vars.items():
        if isinstance(value, list):
            value = ",".join(value)
        extra_vars.extend(["-e", f"{key}='{value}'"])

    executable = _ansible_playbook()
    if not executable:
        logger.error(
            "ansible-playbook not found -- install dmtri's dependencies "
            "(uv sync) or put ansible on PATH")
        if exit_on_error:
            sys.exit(_RC_NOT_FOUND)
        return _RC_NOT_FOUND

    cmd = [
        executable,
        str(playbook_name.resolve()),
        "-i",
        str(inventory.resolve()),
        
    ] + extra_vars


    logger.info(f"Running: {' '.join(str(x) for x in cmd)}")


    out, err, rc = ansible_runner.run_command(
        executable_cmd=executable,
        cmdline_args=cmd[1:], 
        input_fd=sys.stdin,
        output_fd=sys.stdout,
        error_fd=sys.stderr,
    )

    if rc != 0:
        logger.error(f"Playbook {playbook_name} failed with return code {rc}")
        if exit_on_error:
            sys.exit(rc)
        return rc

    logger.info(f"Playbook {playbook_name} completed successfully")
    return rc
