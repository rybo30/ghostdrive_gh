#paths.py

import os
import sys

def get_base_path():
    """Finds the GHOSTDRIVE root folder regardless of OS or packaging."""
    if getattr(sys, 'frozen', False):
        ext_path = os.path.dirname(sys.executable)
        if sys.platform == 'darwin':
            # Mac is still 4 levels deep in the .app bundle
            return os.path.abspath(os.path.join(ext_path, "../../../.."))
        else:
            # WINDOWS: Now only one level up from GHOSTDRIVE/Windows/
            return os.path.abspath(os.path.join(ext_path, ".."))
    else:
        # Running in Dev: C:/GHOSTDRIVE/core/paths.py (Up 1 level)
        return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

BASE_PATH = get_base_path()
CORE_DIR = os.path.join(BASE_PATH, "core")


EVERYTHING_ELSE = os.path.join(CORE_DIR, "Everything_else")

# Data locations inside the nested structure
MODELS_DIR = os.path.join(EVERYTHING_ELSE, "models")
USER_DATA = os.path.join(EVERYTHING_ELSE, "vault") # Storing vault in everything_else
PROJECTS_DIR = os.path.join(EVERYTHING_ELSE, "projects")
INVENTORY_DIR = os.path.join(EVERYTHING_ELSE, "inventory")

# Ensure critical data folders exist
for folder in [USER_DATA, PROJECTS_DIR, INVENTORY_DIR]:
    os.makedirs(folder, exist_ok=True)