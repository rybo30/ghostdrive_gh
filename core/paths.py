# [paths.py]

import os
import sys

def get_base_path():
    """Finds the GHOSTDRIVE root folder regardless of OS or packaging."""
    if getattr(sys, 'frozen', False):
        ext_path = os.path.dirname(sys.executable)
        if sys.platform == 'darwin':
            return os.path.abspath(os.path.join(ext_path, "../../../.."))
        else:
            return os.path.abspath(os.path.join(ext_path, ".."))
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

BASE_PATH = get_base_path()
CORE_DIR = os.path.join(BASE_PATH, "core")
EVERYTHING_ELSE = os.path.join(CORE_DIR, "Everything_else")

# --- Data Locations ---
MODELS_DIR = os.path.join(EVERYTHING_ELSE, "models")
USER_DATA = os.path.join(EVERYTHING_ELSE, "vault") 
PROJECTS_DIR = os.path.join(EVERYTHING_ELSE, "projects")
INVENTORY_DIR = os.path.join(EVERYTHING_ELSE, "inventory")
WALLET_DIR = os.path.join(CORE_DIR, "wallet") 

# Ensure data folders exist
for folder in [USER_DATA, PROJECTS_DIR, INVENTORY_DIR]:
    os.makedirs(folder, exist_ok=True)