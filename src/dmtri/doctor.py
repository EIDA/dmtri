import logging
import ansible_runner
from dmtri.paths import INVENTORY_FILE

logger = logging.getLogger(__name__)

def run_diagnostics(verbose=False, retries=1):
    logger.info(f"Running connectivity check using inventory: {INVENTORY_FILE}")

    ok_hosts = set()
    unreachable_hosts = set()

    for attempt in range(retries):
        logger.info(f"Attempt {attempt + 1} of {retries}")

        r = ansible_runner.run(
            private_data_dir=".",
            inventory=str(INVENTORY_FILE.resolve()),
            module="ping",
            host_pattern="all",
            quiet=not verbose,
            envvars={
                "ANSIBLE_CACHE_PLUGIN": "memory"  # Disable caching to avoid plugin warnings
            }
        )

        for event in r.events:
            if not isinstance(event, dict):
                continue
            data = event.get("event_data", {})
            host = data.get("host")
            if not host:
                continue
            if event["event"] == "runner_on_ok":
                ok_hosts.add(host)
            elif event["event"] == "runner_on_unreachable":
                unreachable_hosts.add(host)

        # Break early if all hosts responded
        if ok_hosts and not unreachable_hosts:
            break

    logger.info("\nResults:")

    if not ok_hosts and not unreachable_hosts:
        logger.warning("No responses received. Are you connected to the VPN?")
        return

    for host in sorted(ok_hosts):
        logger.info(f"[OK] {host}")
    for host in sorted(unreachable_hosts):
        logger.error(f"[UNREACHABLE] {host}")
