from dotenv import load_dotenv
import os
import logging
import tempfile
import ansible_runner

logger = logging.getLogger(__name__)

def run_diagnostics(verbose=False):
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load .env
    load_dotenv()

    host = os.getenv("DMTRI_HOST")
    user = os.getenv("DMTRI_USER")
    password = os.getenv("DMTRI_PASS")

    if not all([host, user, password]):
        logger.error("Missing DMTRI_HOST / USER / PASS in .env file.")
        return

    logger.info(f"Checking connectivity to {host}...")

    # Create temporary inventory file
    with tempfile.NamedTemporaryFile("w+", delete=False) as tmp_inventory:
        tmp_inventory.write(f"""
[seedpsd_nodes]
{host} ansible_user={user} ansible_ssh_pass="{password}" ansible_ssh_common_args=-o StrictHostKeyChecking=no
        """)
        tmp_inventory_path = tmp_inventory.name

    env = os.environ.copy()
    env["ANSIBLE_TIMEOUT"] = "5"
    env["ANSIBLE_HOST_KEY_CHECKING"] = "False"

    try:
        r = ansible_runner.run(
            private_data_dir=".",
            inventory=tmp_inventory_path,
            module="ping",
            host_pattern="seedpsd_nodes",
            envvars=env,
        )
    except Exception as e:
        logger.error(f" Failed to run Ansible: {e}")
        return

    found = False
    for event in r.events:
        host = event.get("event_data", {}).get("host")
        if event.get("event") == "runner_on_ok":
            logger.info(f"[OK] {host}")
            found = True
        elif event.get("event") == "runner_on_failed":
            logger.warning(f"[FAIL] {host}")
            found = True

    if not found:
        logger.warning("No responses from host.")
