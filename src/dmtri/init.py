import shutil
import logging
from pathlib import Path
import appdirs

from dmtri.paths import DATA_DIR

logger = logging.getLogger(__name__)

USER_CONFIG_DIR = Path(appdirs.user_config_dir("dmtri"))


def run_init(force=False):
    """
    Copy bundled playbooks and inventory into the user config directory
    so the user can customize them.
    """
    if USER_CONFIG_DIR.exists() and not force:
        logger.info(f"Config directory already exists: {USER_CONFIG_DIR}")
        logger.info("Use --force to overwrite existing files.")
        logger.info(f"\nYou can edit the file with: nano {USER_CONFIG_DIR}/hosts.ini")
        return

    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Copy inventory from example
    src_inventory = DATA_DIR / "inventory" / "hosts.ini.example"
    dst_inventory = USER_CONFIG_DIR / "hosts.ini"
    if not dst_inventory.exists() or force:
        shutil.copy2(src_inventory, dst_inventory)
        logger.info(f"  [created] {dst_inventory}")
        logger.info("  ⚠️  Edit hosts.ini with your real host details before running any commands!")
    else:
        logger.info(f"  [skipped] {dst_inventory} (already exists)")


    # Copy playbooks tree
    src_playbooks = DATA_DIR / "playbooks"
    dst_playbooks = USER_CONFIG_DIR / "playbooks"
    if dst_playbooks.exists() and force:
        shutil.rmtree(dst_playbooks)
    if not dst_playbooks.exists():
        shutil.copytree(src_playbooks, dst_playbooks)
        logger.info(f"  [created] {dst_playbooks}/")
    else:
        logger.info(f"  [skipped] {dst_playbooks}/ (already exists, use --force to overwrite)")

    logger.info(f"\nDone! Edit your configuration in: {USER_CONFIG_DIR}")
    logger.info("  - Inventory : " + str(USER_CONFIG_DIR / "hosts.ini"))
    logger.info("  - Playbooks : " + str(USER_CONFIG_DIR / "playbooks/"))
    logger.info(f"\nQuick edit command: nano {USER_CONFIG_DIR}/hosts.ini")
    logger.info("\ndmtri will automatically use your local config on next run.")
