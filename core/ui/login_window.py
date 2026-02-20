import os
import sys
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFrame
from PySide6.QtCore import Qt, QPropertyAnimation, QPoint
from cryptography.fernet import Fernet

from core.identity import get_hardware_locked_identity

# --- ORIGINAL SYSTEM PATHS ---
try:
    from ghostvault import (
        get_vault_paths, load_key_from_passphrase, create_new_user, user_exists
    )
except ImportError:
    from Everything_else.ghostvault import (
        get_vault_paths, load_key_from_passphrase, create_new_user, user_exists
    )

# --- THEME CONFIG ---
from . import style_config
from .style_config import (
    FONT_FAMILY, FONT_SIZE, T,
    COLOR_BG, COLOR_FG, COLOR_ACCENT, COLOR_BUTTON, COLOR_HIGHLIGHT, COLOR_PROTOCOL,
    STYLE_LABEL, STYLE_BUTTON, STYLE_INPUT
)

class LoginWindow(QWidget):
    def __init__(self, on_login_success):
        super().__init__()
        self.on_login_success = on_login_success
        
        # Sleek Frameless Setup
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground) 
        self.setFixedSize(400, 480) 

        # Main Layout
        self.master_layout = QVBoxLayout(self)
        self.master_layout.setContentsMargins(0, 0, 0, 0) # Remove outer padding
        
        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        self.master_layout.addWidget(self.container)
        
        self.layout = QVBoxLayout(self.container)
        # Increased horizontal margins (50) to prevent text clipping
        self.layout.setContentsMargins(50, 30, 50, 40) 
        self.layout.setSpacing(12) 

        # UI Elements
        self.title_label = QLabel("GHOSTDRIVE ACCESS")
        self.title_label.setAlignment(Qt.AlignCenter)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("IDENTIFICATION")

        self.passphrase_input = QLineEdit()
        self.passphrase_input.setPlaceholderText("SECURITY PASSPHRASE")
        self.passphrase_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.login_btn = QPushButton("INITIALIZE LOGIN")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setMinimumHeight(45)
        self.login_btn.clicked.connect(self.try_login)

        self.create_btn = QPushButton("CREATE NEW ACCOUNT")
        self.create_btn.setObjectName("SecondaryBtn")
        self.create_btn.setCursor(Qt.PointingHandCursor)
        self.create_btn.setMinimumHeight(40)
        self.create_btn.clicked.connect(self.create_account)

        # Build Layout
        self.layout.addStretch(2) 
        self.layout.addWidget(self.title_label)
        self.layout.addSpacing(25) 
        
        self.layout.addWidget(self.username_input)
        self.layout.addWidget(self.passphrase_input)
        
        self.layout.addSpacing(15) 
        self.layout.addWidget(self.login_btn)
        self.layout.addWidget(self.create_btn)
        self.layout.addStretch(3) 

        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet("background: transparent;")
        
        # Fixed Font Size (20px) and Letter Spacing (3px) to prevent clipping
        self.title_label.setStyleSheet(f"""
            color: {COLOR_ACCENT}; 
            font-family: '{FONT_FAMILY}'; 
            font-size: 20px; 
            font-weight: 900; 
            border-bottom: 1px solid {COLOR_ACCENT}; 
            padding-bottom: 8px; 
            margin-bottom: 5px;
            letter-spacing: 3px;
        """)

        self.container.setStyleSheet(f"""
            QFrame#MainContainer {{
                background-color: {COLOR_BG};
                border: 2px solid {COLOR_ACCENT};
                border-radius: 20px;
            }}
            {STYLE_INPUT}
            {STYLE_BUTTON}
            QLineEdit {{
                margin-bottom: 5px;
            }}
        """)

    def shake_feedback(self):
        self.anim = QPropertyAnimation(self.container, b"pos")
        self.anim.setDuration(50)
        self.anim.setLoopCount(4)
        curr = self.container.pos()
        self.anim.setKeyValueAt(0, curr)
        self.anim.setKeyValueAt(0.25, curr + QPoint(-10, 0))
        self.anim.setKeyValueAt(0.75, curr + QPoint(10, 0))
        self.anim.setKeyValueAt(1, curr)
        self.anim.start()

    def show_tactical_msg(self, title, text, icon=QMessageBox.Warning):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(icon)
        msg.setStyleSheet(f"background-color: {COLOR_BG}; color: {COLOR_FG}; border: 1px solid {COLOR_ACCENT};")
        return msg.exec()

    def try_login(self):
        username = self.username_input.text().strip()
        passphrase = self.passphrase_input.text().strip()

        if not username or not passphrase:
            self.shake_feedback()
            return

        if not user_exists(username):
            self.shake_feedback()
            return

        try:
            _, salt_path = get_vault_paths(username)
            key = load_key_from_passphrase(passphrase, salt_path)
            fernet = Fernet(key)

            identity_data = get_hardware_locked_identity(username, passphrase, salt_path)
            
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            app.ghost_id = identity_data["identity_pub_hex"]
            app.private_key = identity_data["sync_priv"]
            app.sync_pub_hex = identity_data["sync_pub_hex"]

            import inspect
            sig = inspect.signature(self.on_login_success)
            
            if len(sig.parameters) >= 5:
                self.on_login_success(username, passphrase, fernet, app.ghost_id, app.private_key)
            else:
                self.on_login_success(username, passphrase, fernet)
            
            self.close()

        except Exception as e:
            print(f"DEBUG: {e}")
            self.shake_feedback()

    def create_account(self):
        username = self.username_input.text().strip()
        passphrase = self.passphrase_input.text().strip()

        if not username or not passphrase or user_exists(username):
            self.shake_feedback()
            return

        try:
            create_new_user(username, passphrase)
            self.show_tactical_msg("Success", f"Account created for {username}.", icon=QMessageBox.Information)
        except Exception as e:
            self.show_tactical_msg("Failed", str(e))