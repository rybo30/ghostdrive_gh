# =============================================================================
# jynx_operator_ui.py — Cross-Platform Operator Commands
# Refactored for Portable USB Structure with Delta Force Update Protocol
# =============================================================================

import os
import sys
import datetime
import webbrowser
import requests
import zipfile
import subprocess
import platform
import time
import shutil
from shutil import copytree as copy_tree
from cryptography.fernet import Fernet

# Import GPS from core.paths
from core.paths import EVERYTHING_ELSE

# Import cross-platform functions from core
from core import (
    disconnect_wifi,
    reconnect_wifi, 
    scan_networks,
    blackout_mode as _core_blackout,
    status_report as _core_status_report,
    get_cpu_temperature,
    health_check,
)

# Centralize paths
JOURNAL_DIR = os.path.join(EVERYTHING_ELSE, "journal")
PROMPT_FILE = os.path.join(EVERYTHING_ELSE, "soul_prompts.txt")
FAIL_LOG = os.path.join(EVERYTHING_ELSE, "protocol_err.log")
VERSION_FILE = "version.txt"
os.makedirs(JOURNAL_DIR, exist_ok=True)

# G-DRIVE ANONYMOUS HANDSHAKE
VERSION_ID = '1-p_6i_pW_Fm_R_S3wOAt0_qf3K2j_X6M'
PAYLOAD_ID = '1G_hB_m_Y0J_zL_q9_K2L_oP_x5J_R_m'

# =============================================================================
# Delta Force Update Protocols (Clandestine)
# =============================================================================

def run_update_protocol():
    """The master clandestine update function (Google Drive)."""
    error_count = 0
    if os.path.exists(FAIL_LOG):
        try:
            with open(FAIL_LOG, 'r') as f: error_count = int(f.read().strip())
        except: error_count = 0

    if error_count >= 3:
        return "⚠️ Update protocol deferred: Multiple failure lock."

    try:
        reconnect_to_wifi()
        v_url = f'https://drive.google.com/uc?export=download&id={VERSION_ID}'
        cloud_v = requests.get(v_url, timeout=10).text.strip()
        
        local_v = "1.0.0"
        if os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, "r") as f: local_v = f.read().strip()

        if cloud_v <= local_v:
            return "✅ System is already running the latest protocol."

        z_url = f'https://drive.google.com/uc?export=download&id={PAYLOAD_ID}'
        r = requests.get(z_url, stream=True)
        r.raise_for_status()
        
        tmp_zip = ".tmp_payload.zip"
        with open(tmp_zip, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        staging_dir = ".shadow_staging"
        with zipfile.ZipFile(tmp_zip, 'r') as z:
            z.extractall(staging_dir)
        
        os.remove(tmp_zip)
        if os.path.exists(FAIL_LOG): os.remove(FAIL_LOG)
        with open(".update_ready", "w") as f: f.write(cloud_v)
        
        return "📡 Update staged. Changes will apply on next restart."

    except Exception as e:
        error_count += 1
        with open(FAIL_LOG, 'w') as f: f.write(str(error_count))
        return f"❌ Update protocol interrupted. Error logged ({error_count}/3)."

# =============================================================================
# GitHub Surgical Sync
# =============================================================================
def run_github_surgical_sync():
    r"""
    Downloads the public GhostDrive repo and overlays the 'core' folder
    onto the USB root (D:\), preserving local .gguf files.
    """
    # 1. Determine Paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up levels to reach D:\ from D:\core\Everything_else\
    USB_ROOT = os.path.dirname(os.path.dirname(current_dir))
    LOCAL_CORE = os.path.join(USB_ROOT, "core")

    REPO_URL = "https://github.com/rybo30/ghostdrive_gh/archive/refs/heads/main.zip"
    TEMP_ZIP = os.path.join(USB_ROOT, ".gh_update_payload.zip")
    STAGING_DIR = os.path.join(USB_ROOT, ".gh_staging")

    try:
        # 2. Aggressive Network Handshake
        print("📡 Initializing network handshake...")
        reconnect_to_wifi()
        
        # Give the OS 5 seconds to settle DNS/IP assignment
        print("⏳ Waiting for DNS resolution (5s)...")
        time.sleep(5) 
        
        # 3. Download Payload with Retries
        max_retries = 3
        r_req = None
        
        for attempt in range(max_retries):
            try:
                print(f"📥 Fetching updates (Attempt {attempt+1}/{max_retries})...")
                r_req = requests.get(REPO_URL, stream=True, timeout=20)
                r_req.raise_for_status()
                break # Success!
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                if attempt < max_retries - 1:
                    print("⚠️ Connection failed. Retrying handshake...")
                    reconnect_to_wifi()
                    time.sleep(5)
                else:
                    raise # Rethrow error if final attempt fails

        # 4. Save Payload
        with open(TEMP_ZIP, 'wb') as f:
            for chunk in r_req.iter_content(chunk_size=8192):
                f.write(chunk)

        # 5. Extract to Shadow Staging
        if os.path.exists(STAGING_DIR):
            shutil.rmtree(STAGING_DIR)
        
        with zipfile.ZipFile(TEMP_ZIP, 'r') as z:
            z.extractall(STAGING_DIR)

        # 6. Locate Source and Target
        extracted_root = os.path.join(STAGING_DIR, "ghostdrive_gh-main")
        source_core = os.path.join(extracted_root, "core")

        if not os.path.exists(source_core):
            return "❌ Error: Could not locate 'core' in the repository payload."

        if not os.path.exists(LOCAL_CORE):
            return f"❌ Target Error: {LOCAL_CORE} not found."

        # 7. Execute Surgical Overlay
        print(f"⚡ Target identified: {LOCAL_CORE}")
        print("⚡ Overlaying system files...")
        copy_tree(source_core, LOCAL_CORE)

        # 8. Cleanup
        if os.path.exists(TEMP_ZIP): os.remove(TEMP_ZIP)
        if os.path.exists(STAGING_DIR): shutil.rmtree(STAGING_DIR)

        return "✅ Sync Complete. Root core updated."

    except Exception as e:
        if os.path.exists(TEMP_ZIP): os.remove(TEMP_ZIP)
        if os.path.exists(STAGING_DIR): shutil.rmtree(STAGING_DIR)
        return f"❌ Sync failed: {str(e)}"

# =============================================================================
# Soul Vent (Journal)
# =============================================================================

def get_random_prompt():
    import random
    if not os.path.exists(PROMPT_FILE):
        return "What do I need to let go of today?"
    try:
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            prompts = [line.strip() for line in f if line.strip()]
        return random.choice(prompts) if prompts else "What is on your mind?"
    except Exception:
        return "What do I need to let go of today?"

def soul_vent(filename=None, entry=None, passphrase=None, chosen_prompt=None):
    from filecrypt import get_fernet, encrypt_file
    if not chosen_prompt: chosen_prompt = "Journal Entry"
    if filename:
        filename = f"{filename}.txt" if not filename.endswith(".txt") else filename
    else:
        timestamp = datetime.datetime.now().strftime("%d%b%Y_%I%M%p")
        filename = f"{timestamp}.txt"
    file_path = os.path.join(JOURNAL_DIR, filename)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Prompt: {chosen_prompt}\n\n")
            f.write(entry.strip() + "\n")
    except Exception as e:
        return f"❌ Failed to write journal file: {e}"
    if passphrase:
        try:
            fernet = get_fernet(passphrase)
            encrypt_file(file_path, fernet)
            return "✅ Soul vent written and encrypted."
        except Exception as e:
            return f"❌ Encryption failed: {e}"
    return "⚠️ No passphrase provided — file left unencrypted."

def soul_vent_summon(passphrase):
    from filecrypt import get_fernet, decrypt_file
    if not os.path.exists(JOURNAL_DIR):
        return [], "🪦 No journal folder found."
    fernet = get_fernet(passphrase)
    decrypted_map = {}
    for filename in os.listdir(JOURNAL_DIR):
        if filename.endswith(".enc"):
            enc_path = os.path.join(JOURNAL_DIR, filename)
            try:
                decrypted = decrypt_file(enc_path, fernet)
                decrypted_map[filename] = decrypted
            except: continue
    if not decrypted_map:
        return [], "🪦 No decryptable journal entries found."
    return list(decrypted_map.keys()), decrypted_map

# =============================================================================
# Network & System Protocols
# =============================================================================

def blackout_mode(): return _core_blackout()
def scan_wifi_networks(): return scan_networks()
def reconnect_to_wifi(): return reconnect_wifi()
def status_report(): return _core_status_report()

def activate_big_brother():
    try:
        webbrowser.open("https://chat.openai.com")
        return "Big Brother activated."
    except Exception as e:
        return f"❌ Failed to activate: {e}"

# =============================================================================
# Central Command Dispatcher
# =============================================================================

def execute_command(command_name: str, username: str = "User"):
    try:
        if command_name == "update_payload": 
            result = run_update_protocol() 
            if "staged" in result:
                subprocess.Popen(["python", "silent_bootstrapper.py"], shell=True)
                os._exit(0) 
            return result
        elif command_name == "update":
            return run_github_surgical_sync()
        elif command_name == "blackout_mode": return blackout_mode()
        elif command_name == "reconnect_wifi": return reconnect_to_wifi()
        elif command_name == "scan_networks": return scan_wifi_networks()
        elif command_name == "activate_big_brother": return activate_big_brother()
        elif command_name == "status_report": return status_report()
        elif command_name == "soul_vent": return "Journal system ready."
        elif command_name == "health_check":
            import json
            return json.dumps(health_check(), indent=2)
        else:
            return f"⚠️ Unknown protocol: {command_name}"
    except Exception as e:
        return f"❌ Error while executing '{command_name}': {e}"
