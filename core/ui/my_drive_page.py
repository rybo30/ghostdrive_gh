import os
import tempfile
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QGridLayout, QScrollArea, QMenu, QPushButton, QFileDialog, QInputDialog,
    QLineEdit, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QIcon
from .style_config import T, STYLE_BUTTON, COLOR_ACCENT

class MyDrivePage(QWidget):
    def __init__(self, engine, manifest):
        super().__init__()
        self.engine = engine
        self.manifest = manifest
        self.current_folder = None 
        self.search_query = ""
        
        self.folder_layout = None
        self.grid = None
        
        self.setAcceptDrops(True)
        self.init_ui()
        self.refresh_folders()
        self.refresh_grid()

    def init_ui(self):
        # Main Layout: Deep padding for that "contained" look
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(35, 30, 35, 35)
        self.layout.setSpacing(25)

        # --- 1. TACTICAL HEADER ---
        self.header = QHBoxLayout()
        
        # Interactive Breadcrumb
        self.breadcrumb_frame = QFrame()
        self.breadcrumb_frame.setStyleSheet(f"background: rgba(255,255,255,0.03); border-radius: 10px; padding: 5px 15px;")
        b_layout = QHBoxLayout(self.breadcrumb_frame)
        b_layout.setContentsMargins(10, 5, 10, 5)
        
        self.path_label = QLabel("VAULT ACCESS // ROOT")
        self.path_label.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 11px; font-weight: 900; letter-spacing: 2px;")
        b_layout.addWidget(self.path_label)
        
        # Search Bar with "Neon Focus"
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("SEARCH VAULT...")
        self.search_bar.setFixedWidth(280)
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                background-color: #0d1117;
                border: 1px solid #161b22;
                border-radius: 20px;
                color: {COLOR_ACCENT};
                padding: 10px 18px;
                font-family: 'Consolas'; font-size: 11px;
            }}
            QLineEdit:focus {{ border: 1px solid {COLOR_ACCENT}; background: #121d2f; }}
        """)
        self.search_bar.textChanged.connect(self.update_search)
        
        self.upload_btn = QPushButton(" ⇮ UPLOAD ")
        self.upload_btn.setFixedSize(120, 42)
        self.upload_btn.setCursor(Qt.PointingHandCursor)
        self.upload_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_ACCENT}, stop:1 #1e90ff);
                color: black; font-weight: 900; border-radius: 21px; border: none; font-size: 12px;
            }}
            QPushButton:hover {{ background: white; }}
        """)
        self.upload_btn.clicked.connect(self.open_upload_dialog)

        self.header.addWidget(self.breadcrumb_frame)
        self.header.addStretch()
        self.header.addWidget(self.search_bar)
        self.header.addSpacing(15)
        self.header.addWidget(self.upload_btn)
        self.layout.addLayout(self.header)

        # --- 2. FOLDER HUD ---
        folder_header = QHBoxLayout()
        folder_header.addWidget(QLabel("DIRECTORY TREE", 
            styleSheet=f"color: {T['TEXT_DIM']}; font-size: 10px; font-weight: 900; letter-spacing: 3px;"))
        folder_header.addStretch()
        self.layout.addLayout(folder_header)

        self.folder_scroll = QScrollArea()
        self.folder_scroll.setWidgetResizable(True)
        self.folder_scroll.setFixedHeight(140)
        # Force the scroll area and its viewport to be transparent
        self.folder_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.folder_scroll.viewport().setStyleSheet("background: transparent;")
        self.folder_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.folder_container = QWidget()
        # This is the secret sauce: tells the widget not to paint a background
        self.folder_container.setAttribute(Qt.WA_TranslucentBackground)
        self.folder_container.setStyleSheet("background: transparent; border: none;")
        
        self.folder_layout = QHBoxLayout(self.folder_container)
        self.folder_layout.setContentsMargins(0, 0, 0, 10)
        self.folder_layout.setSpacing(18)
        self.folder_layout.setAlignment(Qt.AlignLeft)

        self.folder_scroll.setWidget(self.folder_container)
        self.layout.addWidget(self.folder_scroll)

        # --- 3. FILE GRID ---
        self.section_title = QLabel("GLOBAL RECENT")
        self.section_title.setStyleSheet(f"color: white; font-size: 13px; font-weight: 900; letter-spacing: 1px; border-bottom: 1px solid #161b22; padding-bottom: 8px;")
        self.layout.addWidget(self.section_title)

        self.file_scroll = QScrollArea()
        self.file_scroll.setWidgetResizable(True)
        # Force transparency here too
        self.file_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.file_scroll.viewport().setStyleSheet("background: transparent;")

        self.grid_widget = QWidget()
        # Same secret sauce for the grid container
        self.grid_widget.setAttribute(Qt.WA_TranslucentBackground)
        self.grid_widget.setStyleSheet("background: transparent; border: none;")
        
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(20)
        self.grid.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.file_scroll.setWidget(self.grid_widget)
        self.layout.addWidget(self.file_scroll)

    # --- THE "COOL" UI GENERATORS ---

    def create_folder_card(self, folder_name):
        card = QFrame()
        card.setObjectName("FolderCard") # This matches the Master Stylesheet
        card.setFixedSize(200, 100)
        card.setCursor(Qt.PointingHandCursor)
        
        is_active = (folder_name == self.current_folder)
        accent = COLOR_ACCENT if is_active else "#161b22"
        bg = "#121d2f" if is_active else "transparent" # Use transparent for inactive

        card.setStyleSheet(f"""
            QFrame#FolderCard {{ 
                background-color: {bg}; 
                background: {bg}; 
                border: 1px solid {accent}; 
                border-radius: 12px; 
            }}
            QFrame#FolderCard:hover {{ 
                border: 1px solid {COLOR_ACCENT}; 
                background: #121d2f; 
            }}
        """)

        # Add shadow/glow if active
        if is_active:
            glow = QGraphicsDropShadowEffect()
            glow.setBlurRadius(15)
            glow.setColor(QColor(COLOR_ACCENT))
            glow.setOffset(0)
            card.setGraphicsEffect(glow)

        l = QVBoxLayout(card)
        l.setContentsMargins(15, 12, 15, 12)
        
        # Icon Row
        icon_row = QHBoxLayout()
        icon = QLabel("📁")
        icon.setStyleSheet("font-size: 20px; border: none; background: transparent;")
        
        status_light = QFrame()
        status_light.setFixedSize(6, 6)
        status_light.setStyleSheet(f"background: {COLOR_ACCENT}; border-radius: 3px;")
        
        icon_row.addWidget(icon)
        icon_row.addStretch()
        if is_active: icon_row.addWidget(status_light)
        l.addLayout(icon_row)

        name = QLabel(folder_name.upper())
        name.setStyleSheet(f"font-weight: 900; color: white; font-size: 11px; letter-spacing: 1px; border: none; background: transparent;")
        l.addWidget(name)
        
        count = len([f for f in self.manifest.get_files() if f.get('folder') == folder_name])
        meta = QLabel(f"SECTOR: {count} OBJECTS")
        meta.setStyleSheet(f"color: {T['TEXT_DIM']}; font-size: 8px; font-weight: 700; border: none; background: transparent;")
        l.addWidget(meta)

        card.mousePressEvent = lambda e: self.filter_by_folder(folder_name)
        return card

    def create_file_card(self, info):
        card = QFrame()
        card.setObjectName("FileCard") # Matches the Master Stylesheet
        card.setFixedSize(170, 180)
        card.setContextMenuPolicy(Qt.CustomContextMenu)
        card.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos, info, card))
        
        ext = info.get('type', '').lower()
        type_color = "#e91e63" if ext == '.pdf' else "#9c27b0" if ext in ['.mp4','.mov'] else COLOR_ACCENT

        # We use !important or specific ID selectors to override style_config
        card.setStyleSheet(f"""
            QFrame#FileCard {{ 
                background-color: transparent; 
                background: none; 
                border: 1px solid #161b22; 
                border-radius: 10px; 
            }}
            QFrame#FileCard:hover {{ 
                border: 1px solid {type_color}; 
                background: rgba(255, 255, 255, 0.02); 
            }}
        """)
        
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 15, 12, 12)

        # Ensure preview is also totally clear
        preview = QFrame()
        preview.setFixedSize(146, 80)
        preview.setStyleSheet("background: transparent; border: none;")
        pl = QVBoxLayout(preview)
        
        emoji = "📕" if ext == '.pdf' else "🎬" if ext in ['.mp4','.mov'] else "📄"
        icon = QLabel(emoji)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 32px; border: none; background: transparent;") # Slightly larger emoji
        pl.addWidget(icon)
        l.addWidget(preview)

        # Content
        name = QLabel(info['name'])
        name.setWordWrap(False) 
        name.setStyleSheet("color: white; font-weight: 800; font-size: 10px; margin-top: 5px; border: none; background: transparent;")
        l.addWidget(name)
        
        size_mb = info.get('size', 0) / (1024*1024)
        l.addStretch()
        
        meta_row = QHBoxLayout()
        size_label = QLabel(f"{size_mb:.1f} MB")
        size_label.setStyleSheet(f"color: {T['TEXT_DIM']}; font-size: 9px; font-weight: 700; border: none; background: transparent;")
        
        type_tag = QLabel(ext.replace('.','').upper())
        type_tag.setStyleSheet(f"color: {type_color}; font-size: 8px; font-weight: 900; border: 1px solid {type_color}; padding: 1px 4px; border-radius: 4px; background: transparent;")
        
        meta_row.addWidget(size_label)
        meta_row.addStretch()
        meta_row.addWidget(type_tag)
        l.addLayout(meta_row)

        # Subtle energy bar at the bottom
        bar = QFrame()
        bar.setFixedHeight(2)
        bar.setStyleSheet(f"background: {type_color}; border-radius: 1px;")
        l.addWidget(bar)

        return card

    # --- LOGIC MAPPING (Same as your provided logic, just tied to new UI) ---
    def update_search(self, text):
        self.search_query = text.lower().strip()
        self.refresh_grid()

    def refresh_folders(self):
        if not self.folder_layout: return
        while self.folder_layout.count():
            item = self.folder_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        # New Folder Card (Tactical Style)
        new_btn = QFrame()
        new_btn.setFixedSize(80, 100)
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setStyleSheet("QFrame { border: 2px dashed #161b22; border-radius: 12px; } QFrame:hover { border: 2px dashed #555; }")
        nl = QVBoxLayout(new_btn)
        n_lbl = QLabel("＋\nNEW")
        n_lbl.setAlignment(Qt.AlignCenter)
        n_lbl.setStyleSheet("color: #555; font-weight: 900; font-size: 10px;")
        nl.addWidget(n_lbl)
        new_btn.mousePressEvent = lambda e: self.add_new_virtual_folder()
        self.folder_layout.addWidget(new_btn)

        for folder in self.manifest.get_folders():
            self.folder_layout.addWidget(self.create_folder_card(folder))
        self.folder_layout.addStretch()

    def refresh_grid(self):
        if not self.grid: return
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        all_files = self.manifest.get_files()
        target = self.current_folder if self.current_folder else "ROOT"
        
        filtered = [f for f in all_files if (self.search_query in f.get('name', '').lower()) and (self.search_query or f.get('folder') == (self.current_folder if self.current_folder else "Recent Files"))]
        
        self.section_title.setText(f"SCANNING: {target}" if not self.search_query else f"SEARCH RESULTS: {self.search_query}")
        self.path_label.setText(f"VAULT ACCESS // {target.upper()}")

        for idx, info in enumerate(filtered):
            self.grid.addWidget(self.create_file_card(info), idx // 5, idx % 5)

    def filter_by_folder(self, name):
        self.current_folder = name if name != self.current_folder else None
        self.search_bar.clear()
        self.refresh_folders()
        self.refresh_grid()

    # (Keep your existing process_file, view_file, decrypt_file, delete_file, and add_new_virtual_folder methods below)
    def open_upload_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "All Files (*.*)")
        if files:
            for f in files: self.process_file(f)
            self.refresh_grid()
            self.refresh_folders()

    def process_file(self, file_path):
        target = self.current_folder if self.current_folder else "Recent Files"
        if os.path.isfile(file_path):
            try:
                fid, size = self.engine.encrypt_file(file_path)
                self.manifest.add_entry(os.path.basename(file_path), fid, size, os.path.splitext(file_path)[1], target)
            except Exception as e: print(e)

    def view_file(self, info):
        try:
            data = self.engine.decrypt_file_to_memory(info['id'])
            temp_path = os.path.join(tempfile.gettempdir(), info['name'])
            with open(temp_path, "wb") as f: f.write(data)
            os.startfile(temp_path) if os.name == 'nt' else subprocess.call(["open", temp_path])
        except Exception as e: print(e)

    def decrypt_file(self, info):
        path, _ = QFileDialog.getSaveFileName(self, "Download File", info['name'])
        if path:
            with open(path, "wb") as f: f.write(self.engine.decrypt_file_to_memory(info['id']))

    def delete_file(self, info):
        self.manifest.remove_entry(info['id'])
        self.refresh_grid()
        self.refresh_folders()

    def add_new_virtual_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder Name:")
        if ok and name:
            self.manifest.add_folder(name)
            self.refresh_folders()

    def show_context_menu(self, pos, info, card):
        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu {{ background: #0d1117; color: white; border: 1px solid #161b22; }} QMenu::item:selected {{ background: {COLOR_ACCENT}; color: black; }}")
        menu.addAction("👁️ VIEW").triggered.connect(lambda: self.view_file(info))
        menu.addAction("📥 DOWNLOAD").triggered.connect(lambda: self.decrypt_file(info))
        menu.addSeparator()
        menu.addAction("🗑️ DELETE").triggered.connect(lambda: self.delete_file(info))
        menu.exec(card.mapToGlobal(pos))

    def dragEnterEvent(self, e): e.accept() if e.mimeData().hasUrls() else e.ignore()
    def dropEvent(self, e):
        for url in e.mimeData().urls(): self.process_file(url.toLocalFile())
        self.refresh_grid()
        self.refresh_folders()