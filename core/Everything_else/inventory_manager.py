import os
import csv
import json
from cryptography.fernet import Fernet

# Import the Universal Path from your new paths.py
from core.paths import EVERYTHING_ELSE

# Define the global inventory directory in the central core
INVENTORY_BASE = os.path.join(EVERYTHING_ELSE, "inventory")
INVENTORY_DIR = INVENTORY_BASE
os.makedirs(INVENTORY_BASE, exist_ok=True)

# ──────────────────────────────────────────────
# 🔒 Dynamic, User-Defined Inventory Manager
# ──────────────────────────────────────────────

DEFAULT_SCHEMA = ["name", "quantity", "location", "last_checked"]

def get_inventory_path(username, sheet_name="inventory"):
    user_dir = os.path.join(INVENTORY_BASE, username)
    os.makedirs(user_dir, exist_ok=True)
    # Standardizing to 'inv_sheetname.enc' prevents the username split confusion
    return os.path.join(user_dir, f"inv_{sheet_name.lower()}.enc")

def list_inventory_sheets(username):
    user_dir = os.path.join(INVENTORY_DIR, username)
    if not os.path.exists(user_dir): return ["inventory"]
    
    # Only look for our new 'inv_' prefix
    files = [f for f in os.listdir(user_dir) if f.startswith("inv_") and f.endswith(".enc")]
    sheets = [f[4:-4] for f in files] # Strips 'inv_' and '.enc'
    return sheets if sheets else ["inventory"]

def rename_inventory_file(username, old_id, new_id):
    """Renames the physical .enc file on disk."""    
    user_dir = os.path.join(INVENTORY_DIR, username)
    old_path = os.path.join(user_dir, f"{username}_{old_id}.enc")
    new_path = os.path.join(user_dir, f"{username}_{new_id}.enc")
    
    if os.path.exists(new_path):
        return False, "A sheet with that name already exists."
    
    try:
        os.rename(old_path, new_path)
        return True, None
    except Exception as e:
        return False, str(e)


def load_inventory(username, fernet: Fernet, sheet_name="inventory"):
    """Load inventory and schema for a specific sheet."""
    filepath = get_inventory_path(username, sheet_name) # Pass sheet_name here
    
    DEFAULT_SCHEMA = ["name", "quantity", "location", "last_checked"]
    
    if not os.path.exists(filepath):
        return {"schema": DEFAULT_SCHEMA, "data": []}

    try:
        with open(filepath, "rb") as f:
            decrypted = fernet.decrypt(f.read()).decode("utf-8")
            payload = json.loads(decrypted)

            if isinstance(payload, list):
                return {"schema": DEFAULT_SCHEMA, "data": payload}

            return payload
    except Exception as e:
        print(f"[ERROR] Failed to decrypt inventory {sheet_name} for {username}: {e}")
        return {"schema": DEFAULT_SCHEMA, "data": []}

# 3. Update save_inventory to accept sheet_name
def save_inventory(username, payload, fernet: Fernet, sheet_name="inventory"):
    """Save full inventory payload to a specific sheet."""
    filepath = get_inventory_path(username, sheet_name)
    try:
        encrypted = fernet.encrypt(json.dumps(payload, indent=2).encode("utf-8"))
        with open(filepath, "wb") as f:
            f.write(encrypted)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save inventory {sheet_name}: {e}")
        return False


# ──────────────────────────────────────────────
# 📤 Export / Import
# ──────────────────────────────────────────────

def export_inventory_to_csv(username, payload, sheet_name="inventory", path=None):
    """Export inventory to a sheet-specific CSV."""
    data = payload.get("data", [])
    schema = payload.get("schema", DEFAULT_SCHEMA)
    all_keys = list(set(schema))

    if path is None:
        user_dir = os.path.join(INVENTORY_BASE, username)
        # FIX: Dynamically name the export based on the active sheet
        path = os.path.join(user_dir, f"inv_{sheet_name.lower()}_export.csv")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)
    return path

def import_inventory_from_csv(username, fernet, current_payload, sheet_name="inventory", path=None):
    """Import CSV data and overwrite the specific active sheet."""
    if path is None:
        user_dir = os.path.join(INVENTORY_BASE, username)
        path = os.path.join(user_dir, f"inv_{sheet_name.lower()}_export.csv")

    if not os.path.exists(path):
        return False, f"No export file found for {sheet_name}"

    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        # Clear existing data and overwrite with CSV rows
        current_payload["data"] = rows
        
        # Save specifically back to the correct .enc file
        save_inventory(username, current_payload, fernet, sheet_name=sheet_name)
        return True, len(rows)
    except Exception as e:
        return False, str(e)