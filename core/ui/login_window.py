import os
import sys
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PySide6.QtCore import Qt
from cryptography.fernet import Fernet

from core.identity import get_hardware_locked_identity

# System Paths
try:
    from ghostvault import (
        get_vault_paths, load_key_from_passphrase, create_new_user, user_exists
    )
except ImportError:
    from Everything_else.ghostvault import (
        get_vault_paths, load_key_from_passphrase, create_new_user, user_exists
    )

# Import the config
from . import style_config
from .style_config import (
    FONT_FAMILY, FONT_SIZE,
    COLOR_BG, COLOR_FG, COLOR_ACCENT, COLOR_BUTTON, COLOR_HIGHLIGHT,
    STYLE_LABEL, STYLE_BUTTON
)

class LoginWindow(QWidget):
    def __init__(self, on_login_success):
        super().__init__()
        self.on_login_success = on_login_success
        self.setWindowTitle("GhostDrive Login")
        self.setFixedSize(380, 450) # Fixed size keeps the "tight" look consistent

        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 30, 40, 30) # Breathing room on sides
        self.layout.setSpacing(10) # Uniform spacing between groups

        # UI Elements
        self.title_label = QLabel("GHOSTDRIVE ACCESS")
        self.title_label.setAlignment(Qt.AlignCenter)
        
        # Username Group
        self.user_lbl = QLabel("Username")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter identification...")

        # Passphrase Group
        self.pass_lbl = QLabel("Passphrase")
        self.passphrase_input = QLineEdit()
        self.passphrase_input.setPlaceholderText("Enter secure key...")
        self.passphrase_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.login_btn = QPushButton("Login")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.try_login)

        self.create_btn = QPushButton("Create New Account")
        self.create_btn.setCursor(Qt.PointingHandCursor)
        self.create_btn.clicked.connect(self.create_account)

        # Build the Layout with controlled spacing
        self.layout.addStretch(1) # Top spacer to push content down slightly
        self.layout.addWidget(self.title_label)
        self.layout.addSpacing(30) # Gap after title
        
        self.layout.addWidget(self.user_lbl)
        self.layout.addWidget(self.username_input)
        self.layout.addSpacing(5) # Tight gap between label and its input
        
        self.layout.addWidget(self.pass_lbl)
        self.layout.addWidget(self.passphrase_input)
        
        self.layout.addSpacing(25) # Gap before buttons
        self.layout.addWidget(self.login_btn)
        self.layout.addWidget(self.create_btn)
        self.layout.addStretch(2) # Bottom stretch to keep everything compact above it

        self.apply_theme()

    def apply_theme(self):
        """Applies the custom colors to the login window components."""
        # Window Background
        self.setStyleSheet(f"background-color: {COLOR_BG};")

        # Labels
        label_css = f"color: {COLOR_FG}; font-family: '{FONT_FAMILY}'; font-weight: bold;"
        self.title_label.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 18px; font-weight: bold;")
        self.user_lbl.setStyleSheet(label_css)
        self.pass_lbl.setStyleSheet(label_css)

        # Inputs
        input_css = f"""
            QLineEdit {{
                background-color: {COLOR_BUTTON};
                color: {COLOR_FG};
                border: 1px solid {COLOR_ACCENT};
                border-radius: 5px;
                padding: 8px;
            }}
        """
        self.username_input.setStyleSheet(input_css)
        self.passphrase_input.setStyleSheet(input_css)

        # Buttons
        self.login_btn.setStyleSheet(STYLE_BUTTON)
        self.create_btn.setStyleSheet(STYLE_BUTTON)

    def try_login(self):
        username = self.username_input.text().strip()
        passphrase = self.passphrase_input.text().strip()

        def show_msg(title, text, icon=QMessageBox.Warning):
            msg = QMessageBox(self)
            msg.setWindowTitle(title)
            msg.setText(text)
            msg.setIcon(icon)
            msg.setStyleSheet("QLabel{ color: black; font-weight: bold; } QPushButton{ color: black; min-width: 80px; }")
            return msg.exec()

        if not username or not passphrase:
            show_msg("Login Failed", "Identification required.")
            return

        if not user_exists(username):
            show_msg("Login Failed", f"Account '{username}' not found.")
            return

        try:
            _, salt_path = get_vault_paths(username)
            key = load_key_from_passphrase(passphrase, salt_path)
            fernet = Fernet(key)

            # 1. Capture the identity dictionary
            identity_data = get_hardware_locked_identity(username, passphrase, salt_path)
            
            # 2. Extract exactly what you need from the dict
            ghost_id = identity_data["identity_pub_hex"]
            private_key = identity_data["sync_priv"]
            public_sync_hex = identity_data["sync_pub_hex"]
            
            # --- 🆕 COMPATIBILITY BRIDGE ---
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            app.ghost_id = ghost_id
            app.private_key = private_key
            app.sync_pub_hex = public_sync_hex 
            # -------------------------------

            # Check if the original success function can handle 5 arguments
            import inspect
            sig = inspect.signature(self.on_login_success)
            
            if len(sig.parameters) >= 5:
                # Pass the updated variables
                self.on_login_success(username, passphrase, fernet, ghost_id, private_key)
            else:
                self.on_login_success(username, passphrase, fernet)
            
            self.close()

        except Exception as e:
            show_msg("Login Failed", f"Decryption Error: {str(e)}")

    def create_account(self):
        username = self.username_input.text().strip()
        passphrase = self.passphrase_input.text().strip()

        if not username or not passphrase:
            QMessageBox.warning(self, "Error", "Fields cannot be empty.")
            return

        if user_exists(username):
            QMessageBox.warning(self, "Error", "User already exists.")
            return

        try:
            create_new_user(username, passphrase)
            QMessageBox.information(self, "Success", f"Account created for {username}.")
        except Exception as e:
            QMessageBox.warning(self, "Failed", str(e))