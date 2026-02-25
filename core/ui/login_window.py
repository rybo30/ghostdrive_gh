# [login_window.py]

import os
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QFrame, QApplication
)
from PySide6.QtCore import Qt, QPropertyAnimation, QPoint, QTimer
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
from .style_config import (
    FONT_FAMILY, T, COLOR_BG, COLOR_FG, COLOR_ACCENT, 
    STYLE_INPUT, STYLE_BUTTON
)

class LoginWindow(QWidget):
    def __init__(self, on_login_success):
        super().__init__()
        self.on_login_success = on_login_success
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground) 
        self.setFixedSize(400, 480) 

        self.master_layout = QVBoxLayout(self)
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        
        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        self.master_layout.addWidget(self.container)
        
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(50, 30, 50, 40) 
        self.layout.setSpacing(12) 

        self.title_label = QLabel("GHOSTDRIVE ACCESS")
        self.title_label.setAlignment(Qt.AlignCenter)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("IDENTIFICATION")

        self.passphrase_input = QLineEdit()
        self.passphrase_input.setPlaceholderText("SECURITY PASSPHRASE")
        self.passphrase_input.setEchoMode(QLineEdit.EchoMode.Password)

        # Status indicator (e.g., "Logging username in...")
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"color: {T['TEXT_DIM']}; font-size: 10px; font-weight: 700; letter-spacing: 1px;")

        self.login_btn = QPushButton("INITIALIZE LOGIN")
        self.login_btn.setObjectName("LoginBtn")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setMinimumHeight(45)
        self.login_btn.clicked.connect(self.try_login)

        self.create_btn = QPushButton("CREATE NEW ACCOUNT")
        self.create_btn.setObjectName("SecondaryBtn")
        self.create_btn.setCursor(Qt.PointingHandCursor)
        self.create_btn.setMinimumHeight(40)
        self.create_btn.clicked.connect(self.create_account)

        self.layout.addStretch(2) 
        self.layout.addWidget(self.title_label)
        self.layout.addSpacing(25) 
        self.layout.addWidget(self.username_input)
        self.layout.addWidget(self.passphrase_input)
        self.layout.addSpacing(10)
        self.layout.addWidget(self.status_label) 
        self.layout.addWidget(self.login_btn)
        self.layout.addWidget(self.create_btn)
        self.layout.addStretch(3) 

        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet("background: transparent;")
        self.container.setStyleSheet(f"""
            QFrame#MainContainer {{
                background-color: {COLOR_BG};
                border: 2px solid {COLOR_ACCENT};
                border-radius: 20px;
            }}
            {STYLE_INPUT}
            {STYLE_BUTTON}
            
            QPushButton#LoginBtn[success="true"] {{
                background-color: #2ea043;
                border: 1px solid #3fb950;
                color: white;
            }}

            QLabel#Title {{
                color: {COLOR_ACCENT}; 
                font-family: '{FONT_FAMILY}'; 
                font-size: 20px; 
                font-weight: 900; 
                border-bottom: 1px solid {COLOR_ACCENT}; 
                padding-bottom: 8px; 
                margin-bottom: 5px;
                letter-spacing: 3px;
            }}
        """)
        self.title_label.setObjectName("Title")

    def create_account(self):
        username = self.username_input.text().strip()
        passphrase = self.passphrase_input.text().strip()

        if not username or not passphrase or user_exists(username):
            self.shake_feedback()
            return

        try:
            create_new_user(username, passphrase)
            self.login_btn.setText("IDENTITY SECURED")
            self.login_btn.setProperty("success", True)
            self.login_btn.style().unpolish(self.login_btn)
            self.login_btn.style().polish(self.login_btn)
            
            self.status_label.setText(f"LOGGING {username.upper()} IN...")
            
            self.username_input.setEnabled(False)
            self.passphrase_input.setEnabled(False)
            self.create_btn.hide()

            QTimer.singleShot(1200, self.try_login)
            
        except Exception as e:
            self.show_tactical_msg("Failed", str(e))

    def try_login(self):
        username = self.username_input.text().strip()
        passphrase = self.passphrase_input.text().strip()

        if not username or not passphrase:
            self.shake_feedback()
            return

        # Status update
        self.status_label.setText(f"LOGGING {username.upper()} IN...")
        QApplication.processEvents() # Now defined via imports

        try:
            _, salt_path = get_vault_paths(username)
            key = load_key_from_passphrase(passphrase, salt_path)
            fernet = Fernet(key)

            identity_data = get_hardware_locked_identity(username, passphrase, salt_path)
            
            app = QApplication.instance()
            app.ghost_id = identity_data["identity_pub_hex"]
            app.private_key = identity_data["sync_priv"]

            self.on_login_success(username, passphrase, fernet)
            self.close()

        except Exception as e:
            print(f"--- LOGIN CRASH: {e} ---") # THIS WILL SHOW THE REAL ERROR IN TERMINAL
            import traceback
            traceback.print_exc()
            self.status_label.setText("AUTHENTICATION FAILED")
            self.shake_feedback()

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