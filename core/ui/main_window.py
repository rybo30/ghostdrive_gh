import os
import sys
import shutil
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QStackedWidget, QLabel, QFrame, QApplication, 
    QGraphicsDropShadowEffect, QProgressBar
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QColor

# --- Logic & Path Imports ---
from core.paths import USER_DATA, BASE_PATH  
from core.Everything_else.manifest_manager import ManifestManager
from core.Everything_else.encryption_engine import GhostEngine

# --- Style Imports ---
from .style_config import get_master_stylesheet, T, COLOR_BG, COLOR_ACCENT, COLOR_FG

# --- Page Imports ---
from .my_drive_page import MyDrivePage
from .chat_page import ChatPage
from .vault_page import VaultPage
from .project_page import ProjectsPage
from .inventory_page import InventoryPage
from .profile_page import ProfilePage
from .sync_page import SyncPage

class GhostDriveMainWindow(QMainWindow):
    def __init__(self, username, passphrase, fernet):
        super().__init__()
        self.username = username
        self.passphrase = passphrase
        self.fernet = fernet
        
        self._drag_pos = QPoint()

        # Identity Detection
        app = QApplication.instance()
        self.ghost_id = getattr(app, "ghost_id", "ID_NOT_FOUND")
        self.private_key = getattr(app, "private_key", None)

        self.engine = GhostEngine(self.fernet) 
        self.manifest = ManifestManager(self.engine, self.username)

        # --- FRAMELESS CONFIG ---
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setMinimumSize(1120, 770) 
        self.setAcceptDrops(True) 

        # Main Wrapper
        self.main_container = QWidget()
        self.setCentralWidget(self.main_container)
        self.main_layout = QVBoxLayout(self.main_container)
        self.main_layout.setContentsMargins(10, 10, 10, 10) 

        # The Actual Visual Program
        self.root_widget = QFrame()
        self.root_widget.setObjectName("RootWidget")
        self.main_layout.addWidget(self.root_widget)

        # Apply Neon Glow Effect
        self.glow = QGraphicsDropShadowEffect()
        self.glow.setBlurRadius(15)
        self.glow.setXOffset(0)
        self.glow.setYOffset(0)
        self.glow.setColor(QColor(COLOR_ACCENT)) 
        self.root_widget.setGraphicsEffect(self.glow)

        self.root_layout = QHBoxLayout(self.root_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # --- SIDEBAR ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(260)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(20, 30, 20, 30)
        self.sidebar_layout.setSpacing(8)

        self.logo_label = QLabel("GHOSTDRIVE")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet(f"font-size: 20px; font-weight: 900; color: {COLOR_ACCENT}; letter-spacing: 4px; padding-bottom: 20px; border: none;")
        self.sidebar_layout.addWidget(self.logo_label)
        
        self.nav_map = {
            "THE VAULT": "My Drive",
            "GHOST KEYS": "Password Vault",
            "MISSIONS": "Projects",
            "INTEL": "Inventory",
            "AI COUNCIL": "Chat",
            "SIGNATURE": "Profile",
            "UPLINK": "Sync"
        }

        self.nav_buttons = {}
        for name in self.nav_map.keys():
            btn = QPushButton(name)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setFixedHeight(45)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(self.handle_nav_click)
            self.sidebar_layout.addWidget(btn)
            self.nav_buttons[name] = btn

        self.sidebar_layout.addStretch()
        
        # --- TACTICAL USER CARD (Storage HUD) ---
        self.user_card = QFrame()
        self.user_card.setObjectName("UserCard")
        self.user_card.setFixedHeight(100)
        self.user_card.setStyleSheet(f"""
            QFrame#UserCard {{
                background: #0d1117; 
                border: 1px solid #161b22; 
                border-radius: 8px;
            }}
        """)
        u_layout = QVBoxLayout(self.user_card)
        u_layout.setContentsMargins(12, 12, 12, 12)
        u_layout.setSpacing(4)

        # Operator ID Row
        self.user_name_label = QLabel(f"OPERATOR: {self.username.upper()}")
        self.user_name_label.setStyleSheet(f"font-weight: 900; color: {COLOR_FG}; font-size: 10px; border: none;")
        u_layout.addWidget(self.user_name_label)

        # Storage Label
        total, used, free = shutil.disk_usage(BASE_PATH)
        free_gb = free // (2**30)
        used_pct = int((used / total) * 100)
        
        self.storage_label = QLabel(f"STORAGE: {free_gb}GB AVAILABLE")
        self.storage_label.setStyleSheet(f"color: {T['TEXT_DIM']}; font-size: 9px; font-weight: 700; border: none;")
        u_layout.addWidget(self.storage_label)

        # Cool Tactical Progress Bar
        self.storage_bar = QProgressBar()
        self.storage_bar.setFixedHeight(6)
        self.storage_bar.setTextVisible(False)
        self.storage_bar.setRange(0, 100)
        self.storage_bar.setValue(used_pct)
        self.storage_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #070a0e;
                border: 1px solid #161b22;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_ACCENT};
                border-radius: 2px;
            }}
        """)
        u_layout.addWidget(self.storage_bar)

        self.sidebar_layout.addWidget(self.user_card)

        # --- CONTENT AREA ---
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        self.header = QFrame()
        self.header.setObjectName("Header") 
        self.header.setFixedHeight(60)
        self.header_layout = QHBoxLayout(self.header)
        self.header_layout.setContentsMargins(30, 0, 15, 0)
        
        self.header_title = QLabel("THE VAULT")
        self.header_title.setStyleSheet(f"font-size: 20px; font-weight: 900; color: {COLOR_FG}; border: none;")
        self.header_layout.addWidget(self.header_title)
        self.header_layout.addStretch()

        # WINDOW CONTROLS
        self.min_btn = QPushButton("—")
        self.min_btn.setObjectName("WindowCtrl")
        self.min_btn.clicked.connect(self.showMinimized)
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("WindowCtrlClose")
        self.close_btn.clicked.connect(self.close)
        
        self.header_layout.addWidget(self.min_btn)
        self.header_layout.addWidget(self.close_btn)

        # STACKED PAGES
        self.stack = QStackedWidget()
        self.pages = {
            "My Drive": MyDrivePage(self.engine, self.manifest),
            "Chat": ChatPage(username, passphrase, fernet),
            "Profile": ProfilePage(username, fernet),
            "Password Vault": VaultPage(username, passphrase, fernet),
            "Projects": ProjectsPage(username, passphrase, fernet),
            "Inventory": InventoryPage(username, passphrase, fernet),
            "Sync": SyncPage(username, fernet, self.ghost_id, self.private_key)
        }
        for page in self.pages.values(): self.stack.addWidget(page)

        self.content_layout.addWidget(self.header)
        self.content_layout.addWidget(self.stack)
        self.root_layout.addWidget(self.sidebar)
        self.root_layout.addWidget(self.content_area)

        self.apply_tactical_styles()
        self.nav_buttons["THE VAULT"].setChecked(True)
        self.center_window()

    def center_window(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.header.underMouse():
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.header.underMouse():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def apply_tactical_styles(self):
        self.setStyleSheet(f"""
            QFrame#RootWidget {{ 
                background-color: {COLOR_BG}; 
                border: 2px solid {COLOR_ACCENT}; 
                border-radius: 12px; 
            }}
            QFrame#Sidebar {{ 
                background-color: #070a0e; 
                border-right: 1px solid #161b22; 
                border-top-left-radius: 10px; 
                border-bottom-left-radius: 10px; 
            }}
            QFrame#Header {{ background: transparent; border-bottom: 1px solid #161b22; }}
            
            QPushButton#NavButton {{
                background: transparent; color: {T['TEXT_DIM']}; border: none;
                text-align: left; padding-left: 15px; font-weight: 700;
            }}
            QPushButton#NavButton:checked {{
                color: {COLOR_ACCENT}; background: #121d2f; border-left: 3px solid {COLOR_ACCENT};
            }}
            
            QPushButton#WindowCtrl, QPushButton#WindowCtrlClose {{
                background: transparent; color: {T['TEXT_DIM']}; font-size: 16px; width: 30px; border: none;
            }}
            QPushButton#WindowCtrlClose:hover {{ color: #ff4444; }}
            QPushButton#WindowCtrl:hover {{ color: {COLOR_ACCENT}; }}
        """)

    def handle_nav_click(self):
        sender = self.sender()
        for btn in self.nav_buttons.values(): btn.setChecked(False)
        sender.setChecked(True)
        logical_key = self.nav_map.get(sender.text().strip())
        if logical_key in self.pages:
            self.stack.setCurrentWidget(self.pages[logical_key])
            self.header_title.setText(sender.text().strip())

    def dragEnterEvent(self, e): 
        if e.mimeData().hasUrls(): e.acceptProposedAction()
    def dropEvent(self, e):
        files = [u.toLocalFile() for u in e.mimeData().urls()]
        if isinstance(self.stack.currentWidget(), MyDrivePage):
            self.stack.currentWidget().handle_dropped_files(files)