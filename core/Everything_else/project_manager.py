import os
import json
from cryptography.fernet import Fernet

# Import the base GPS coordinates from core.paths
from core.paths import EVERYTHING_ELSE

def get_user_project_dir(username):
    """Returns the path to a specific user's project folder anchored in Everything_else."""
    # This ensures projects ALWAYS live inside Everything_else/projects/
    base_projects = os.path.join(EVERYTHING_ELSE, "projects")
    user_dir = os.path.join(base_projects, username)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def load_project_file(username, filename, fernet: Fernet):
    """Refined to handle both full paths or just filenames for the specific user."""
    try:
        # If it's just the filename, build the full path
        if not os.path.isabs(filename):
            user_dir = get_user_project_dir(username)
            filepath = os.path.join(user_dir, filename)
        else:
            filepath = filename

        if not os.path.exists(filepath):
            return None
            
        with open(filepath, "rb") as f:
            encrypted = f.read()
        decrypted = fernet.decrypt(encrypted).decode("utf-8")
        return json.loads(decrypted)
    except Exception as e:
        print(f"[ERROR] Failed to decrypt project file: {e}")
        return None

def list_project_files(username):
    """Lists just the filenames (cleaner for the UI list)."""
    user_dir = get_user_project_dir(username)
    if not os.path.exists(user_dir):
        return []
    # Return just the filenames so the UI doesn't have to strip paths manually
    return [f for f in os.listdir(user_dir) if f.endswith(".enc")]

def save_project_file(username, data, fernet: Fernet):
    """Saves an encrypted project file into the user's specific project folder."""
    try:
        project_name = data.get("project", "untitled_project").replace(" ", "_")
        filename = f"{project_name}.enc"
        
        # Explicitly route to Everything_else/projects/[username]/[filename].enc
        user_dir = get_user_project_dir(username)
        filepath = os.path.join(user_dir, filename)
        
        encrypted = fernet.encrypt(json.dumps(data, indent=2).encode("utf-8"))
        with open(filepath, "wb") as f:
            f.write(encrypted)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save project for {username}: {e}")
        return False

def delete_project_file(filepath):
    """Deletes a specific project file."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    except Exception as e:
        print(f"[ERROR] Failed to delete project file {filepath}: {e}")
        return False


def update_task_status(username, project_data, task_text, new_status, fernet):
    """Updates a specific task's status and saves the project."""
    for task in project_data.get("tasks", []):
        if task["task"] == task_text:
            task["status"] = new_status
            break
    return save_project_file(username, project_data, fernet)