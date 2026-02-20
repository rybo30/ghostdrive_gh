import json
import os
from core.ui.style_config import T
from core.paths import USER_DATA 

class ManifestManager:
    def __init__(self, engine, username="default"):
        # Catch if login logic passes a string path instead of engine object
        self.engine = None if isinstance(engine, str) else engine
        self.username = username
        self.vault_path = USER_DATA 
        
        # Initialize manifest_file as None to prevent "default" file creation
        self.manifest_file = None 
        self.data = {"files": [], "folders": ["Personal"]}
        
        # Only set the file and load if we aren't on the 'default' placeholder
        if self.engine and self.username != "default":
            self.manifest_file = os.path.join(self.vault_path, f"vault_manifest_{self.username}.enc")
            self._load()

    def set_engine(self, engine, username=None):
        """Called by login logic to pivot from 'default' to the real user"""
        if isinstance(engine, str): return # Safety check
        
        self.engine = engine
        if username:
            self.username = username
        
        # Re-map path based on the current USB drive letter in USER_DATA
        self.vault_path = USER_DATA
        self.manifest_file = os.path.join(self.vault_path, f"vault_manifest_{self.username}.enc")
        self._load()

    def _load(self):
        if self.manifest_file and os.path.exists(self.manifest_file) and self.engine:
            try:
                decrypted_data = self.engine.decrypt_file_to_memory_direct(self.manifest_file)
                self.data = json.loads(decrypted_data)
            except Exception as e:
                print(f"Manifest Load Error: {e}")

    def save(self):
        # BLOCKER: If we don't have a user, don't write anything.
        if not self.engine or not self.manifest_file or self.username == "default":
            return

        json_data = json.dumps(self.data, indent=4).encode()
        encrypted_token = self.engine.fernet.encrypt(json_data)
        
        with open(self.manifest_file, "wb") as f:
            f.write(encrypted_token)

    def add_entry(self, name, id, size, file_type, folder="Recent Files"):
        entry = {
            "id": id, "name": name, "size": size,
            "type": file_type, "folder": folder, "date": "2026-02-17" 
        }
        self.data["files"].append(entry)
        self.save()
    
    def get_files(self):
        return self.data.get("files", [])

    def get_folders(self):
        return self.data.get("folders", [])

    def add_folder(self, folder_name):
        if folder_name not in self.data["folders"]:
            self.data["folders"].append(folder_name)
            self.save()

    def remove_entry(self, file_id):
        self.data["files"] = [f for f in self.data["files"] if f["id"] != file_id]
        self.save()

    def update_file_folder(self, file_id, new_folder):
        for file in self.data["files"]:
            if file["id"] == file_id:
                file["folder"] = new_folder
                break
        self.save()