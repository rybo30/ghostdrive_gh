import os
import sys
import json
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStackedWidget, QMainWindow, QLabel, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from .sync_page import SyncPage

# --- BOOTSTRAP: DYNAMIC ROOT DETECTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Safe Import for paths.py
try:
    from paths import EVERYTHING_ELSE
except ImportError:
    from core.paths import EVERYTHING_ELSE

from .chat_page import ChatPage
from .vault_page import VaultPage
from .project_page import ProjectsPage
from .inventory_page import InventoryPage
from .profile_page import ProfilePage

from .style_config import (
    COLOR_BG, COLOR_FG, COLOR_ACCENT, COLOR_BUTTON, 
    get_main_stylesheet, get_viking_icon
)

class GhostDriveMainWindow(QMainWindow):
    def __init__(self, username, passphrase, fernet, ghost_id=None, private_key=None, debug=False):
        super().__init__()
        self.username = username
        self.passphrase = passphrase
        self.fernet = fernet
        self.ghost_id = ghost_id
        self.private_key = private_key

        app = QApplication.instance()
        self.ghost_id = getattr(app, "ghost_id", "ID_NOT_FOUND")
        self.private_key = getattr(app, "private_key", None)
        
        self.current_theme = {
            "COLOR_BG": COLOR_BG, "COLOR_FG": COLOR_FG,
            "COLOR_ACCENT": COLOR_ACCENT, "COLOR_BUTTON": COLOR_BUTTON
        }
        
        profile_path = os.path.join(project_root, "Everything_else", "vault", f"{username}_profile.enc")
        
        if os.path.exists(profile_path):
            try:
                with open(profile_path, "rb") as f:
                    decrypted_data = self.fernet.decrypt(f.read())
                    data = json.loads(decrypted_data)
                    self.current_theme = data.get("theme", self.current_theme)
            except Exception as e:
                print(f"Theme Load Error: {e}")

        self.setWindowTitle("GhostDrive")
        self.setWindowIcon(get_viking_icon())
        self.setMinimumSize(1000, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- SIDEBAR ---
        self.sidebar = QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sidebar_layout.setContentsMargins(10, 20, 10, 10)
        self.sidebar_layout.setSpacing(10)
        self.sidebar.setFixedWidth(180)

        self.buttons = {}
        nav_items = ["Chat", "Profile", "Password Vault", "Projects", "Inventory", "Sync"]
        
        for name in nav_items:
            # Reverted to clean, standard names
            btn = QPushButton(name)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(self.change_page)
            self.sidebar_layout.addWidget(btn)
            self.buttons[name] = btn

        root_layout.addWidget(self.sidebar)

        # --- MAIN STACK ---
        self.stack = QStackedWidget()
        self.pages = {
            "Chat": ChatPage(username, passphrase, fernet),
            "Profile": ProfilePage(username, fernet),
            "Password Vault": VaultPage(username, passphrase, fernet),
            "Projects": ProjectsPage(username, passphrase, fernet),
            "Inventory": InventoryPage(username, passphrase, fernet),
            "Sync": SyncPage(username, fernet, self.ghost_id, self.private_key)
        }
        
        self.pages["Profile"].theme_changed.connect(self.update_system_theme)

        for name in nav_items:
            self.stack.addWidget(self.pages[name])

        root_layout.addWidget(self.stack)
        self.stack.setCurrentWidget(self.pages["Chat"])
        self.refresh_ui_design(self.current_theme)

    def refresh_ui_design(self, theme_dict):
        self.current_theme = theme_dict
        self.setStyleSheet(get_main_stylesheet(theme_dict))
        
        sidebar_bg = theme_dict.get('COLOR_BUTTON', COLOR_BUTTON)
        sidebar_accent = theme_dict.get('COLOR_ACCENT', COLOR_ACCENT)
        self.sidebar.setStyleSheet(f"background-color: {sidebar_bg}; border-right: 1px solid {sidebar_accent};")
        
        current_widget = self.stack.currentWidget()
        for name, btn in self.buttons.items():
            is_active = (self.pages[name] == current_widget)
            bg = theme_dict.get('COLOR_ACCENT', COLOR_ACCENT) if is_active else theme_dict.get('COLOR_BUTTON', COLOR_BUTTON)
            txt = "#ffffff" if is_active else theme_dict.get('COLOR_FG', COLOR_FG)
            
            # Clean, unified style for all buttons
            btn.setStyleSheet(f"""
                QPushButton {{ 
                    background-color: {bg}; 
                    color: {txt}; 
                    border: 1px solid {sidebar_accent}; 
                    padding: 8px; 
                    border-radius: 5px; 
                    font-weight: bold; 
                    font-size: 13px; 
                }}
            """)

    def update_system_theme(self, theme_dict):
        self.refresh_ui_design(theme_dict)
        for page in self.pages.values():
            if hasattr(page, "apply_dynamic_theme"):
                page.apply_dynamic_theme(theme_dict)

    def change_page(self):
        btn = self.sender()
        if btn:
            # Direct string match—no more [BETA] tag issues
            label = btn.text()
            if label in self.pages:
                self.stack.setCurrentWidget(self.pages[label])
                self.refresh_ui_design(self.current_theme)