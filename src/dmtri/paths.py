from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent      
SRC_DIR = MODULE_DIR.parent                       
                    


PLAYBOOKS_DIR = SRC_DIR / "playbooks"             
INVENTORY_DIR = SRC_DIR / "inventory"        

# Specific playbooks
PLAYBOOK_SEEDPSD = PLAYBOOKS_DIR / "seedpsd_simulate.yml"
PLAYBOOK_REFRESH = PLAYBOOKS_DIR / "refresh.yml"
PLAYBOOK_ECHO = PLAYBOOKS_DIR / "echo.yml"
PLAYBOOK_CLEAN = PLAYBOOKS_DIR / "clean.yml"

# Inventory file
INVENTORY_FILE = INVENTORY_DIR / "hosts.ini"
