import json
import os
import threading
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QListWidget, QListWidgetItem,
                             QFrame, QApplication, QCheckBox, QStackedWidget, QProgressBar,  
                             QMessageBox, QDialog, QDialogButtonBox, QScrollArea)
from PySide6.QtCore import Qt, Signal

# Style and Path Imports
from ui.style_config import (COLOR_BG, COLOR_FG, COLOR_ACCENT, COLOR_BUTTON, 
                           COLOR_HIGHLIGHT, COLOR_PAGE_BG, COLOR_PROTOCOL, 
                           COLOR_BORDER, FONT_FAMILY, STYLE_BUTTON)
from core.paths import EVERYTHING_ELSE
from core.network_manager import GhostNetwork 

# Logic Imports
from core.peers_manager import delete_peer, load_peers, save_peer

class SyncPage(QWidget):
    def __init__(self, username, fernet, ghost_id, private_key):
        super().__init__()
        self.username = username
        self.fernet = fernet
        self.ghost_id = ghost_id
        self.private_key = private_key
        
        # 1. INITIALIZE NETWORK
        self.network = GhostNetwork(self.username, self.fernet, self.ghost_id, self.private_key)
        
        # Start background threads
        threading.Thread(target=self.network.start_server, daemon=True).start()
        threading.Thread(target=self.network.start_broadcast, daemon=True).start()
        threading.Thread(target=self.network.listen_for_peers, daemon=True).start()
        
        self.setStyleSheet(f"background-color: {COLOR_PAGE_BG}; font-family: '{FONT_FAMILY}';")
        self.init_ui()
        self.refresh_peer_list()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- TOP BAR ---
        id_bar = QFrame()
        id_bar.setFixedHeight(80)
        id_bar.setStyleSheet(f"background-color: {COLOR_BG}; border-bottom: 1px solid {COLOR_BORDER};")
        id_bar_layout = QHBoxLayout(id_bar)
        
        id_info = QVBoxLayout()
        title = QLabel("LOCAL NODE ADDRESS")
        title.setStyleSheet(f"color: {COLOR_PROTOCOL}; font-weight: bold; font-size: 10px; border: none;")
        
        self.id_display = QLineEdit(self.ghost_id)
        self.id_display.setReadOnly(True)
        self.id_display.setStyleSheet(f"background: transparent; border: none; color: {COLOR_ACCENT}; font-size: 12px;")
        
        id_info.addWidget(title)
        id_info.addWidget(self.id_display)
        
        # IP Display Section
        self.my_ip_display = QLineEdit("IP: HIDDEN")
        self.my_ip_display.setReadOnly(True)
        self.my_ip_display.setFixedWidth(120)
        self.my_ip_display.setStyleSheet("color: #555; border: none; background: transparent; font-size: 11px;")
        
        show_ip_btn = QPushButton("SHOW IP")
        show_ip_btn.setFixedWidth(70)
        show_ip_btn.setStyleSheet("font-size: 10px; border: 1px solid #444; color: #888;")
        show_ip_btn.clicked.connect(self.reveal_ip)
        
        copy_btn = QPushButton("COPY ID")
        copy_btn.setStyleSheet(STYLE_BUTTON)
        copy_btn.setFixedWidth(100)
        copy_btn.clicked.connect(self.copy_id)
        
        id_bar_layout.addLayout(id_info)
        id_bar_layout.addStretch()
        id_bar_layout.addWidget(self.my_ip_display)
        id_bar_layout.addWidget(show_ip_btn)
        id_bar_layout.addWidget(copy_btn)
        main_layout.addWidget(id_bar)

        content_row = QHBoxLayout()
        content_row.setSpacing(0)

        # --- SIDEBAR ---
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(260)
        self.sidebar.setStyleSheet(f"background-color: {COLOR_BG}; border-right: 1px solid {COLOR_BORDER};")
        side_layout = QVBoxLayout(self.sidebar)
        
        side_layout.addWidget(QLabel("AUTHORIZED NETWORK"))
        self.peer_list_widget = QListWidget()
        self.peer_list_widget.setStyleSheet(f"""
            QListWidget {{ border: none; background: transparent; color: {COLOR_FG}; outline: none; }}
            QListWidget::item {{ padding: 15px; border-bottom: 1px solid {COLOR_BUTTON}; }}
            QListWidget::item:selected {{ background-color: {COLOR_HIGHLIGHT}; color: {COLOR_FG}; border-left: 3px solid {COLOR_ACCENT}; }}
        """)
        self.peer_list_widget.currentRowChanged.connect(self.display_peer_details)
        side_layout.addWidget(self.peer_list_widget)

        mgmt_layout = QHBoxLayout()
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setStyleSheet(f"font-size: 10px; padding: 5px; color: {COLOR_FG}; border: 1px solid {COLOR_BORDER};")
        self.delete_btn.clicked.connect(self.delete_selected_peer)
        mgmt_layout.addWidget(self.delete_btn)
        side_layout.addLayout(mgmt_layout)
        
        add_btn = QPushButton("+ ADD NEW PEER")
        add_btn.setStyleSheet(STYLE_BUTTON)
        add_btn.clicked.connect(self.add_peer_dialog)
        side_layout.addWidget(add_btn)
        content_row.addWidget(self.sidebar)

        # --- CONFIG AREA ---
        self.right_stack = QStackedWidget()
        empty_msg = QLabel("Select a peer to configure synchronization.")
        empty_msg.setAlignment(Qt.AlignCenter)
        self.right_stack.addWidget(empty_msg)

        self.config_view = QWidget()
        config_layout = QVBoxLayout(self.config_view)
        config_layout.setContentsMargins(30, 30, 30, 30)

        self.peer_title = QLabel("PERMISSIONS")
        self.peer_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLOR_FG}; border: none;")
        config_layout.addWidget(self.peer_title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setSpacing(15)

        self.project_card = self.create_clean_asset_group("PROJECT REPOSITORIES", "project_container")
        self.scroll_layout.addWidget(self.project_card)

        self.inventory_card = self.create_clean_asset_group("INVENTORY DATASETS", "inventory_container")
        self.scroll_layout.addWidget(self.inventory_card)

        scroll.setWidget(scroll_content)
        config_layout.addWidget(scroll)

        # MANUAL IP ENTRY
        self.manual_ip_input = QLineEdit()
        self.manual_ip_input.setPlaceholderText("Target IP (e.g. 72.15.22.4) - Leave blank for Local/Auto")
        self.manual_ip_input.setStyleSheet(f"background: {COLOR_BG}; color: {COLOR_ACCENT}; padding: 10px; border: 1px solid {COLOR_BORDER}; margin-bottom: 5px;")
        config_layout.addWidget(self.manual_ip_input)

        # PROGRESS BAR
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{ border: 1px solid {COLOR_BORDER}; border-radius: 2px; text-align: center; color: {COLOR_FG}; height: 10px; font-size: 8px; }}
            QProgressBar::chunk {{ background-color: {COLOR_ACCENT}; }}
        """)
        self.progress_bar.hide()
        config_layout.addWidget(self.progress_bar)

        self.save_btn = QPushButton("SAVE INITIALIZE HANDSHAKE")
        self.save_btn.setStyleSheet(STYLE_BUTTON)
        self.save_btn.setFixedHeight(45)
        self.save_btn.clicked.connect(self.initiate_handshake)
        config_layout.addWidget(self.save_btn)

        self.right_stack.addWidget(self.config_view)
        content_row.addWidget(self.right_stack)
        main_layout.addLayout(content_row)

    def reveal_ip(self):
        ip = self.network.get_public_ip()
        self.my_ip_display.setText(ip)
        self.my_ip_display.setStyleSheet(f"color: {COLOR_ACCENT}; border: none; background: transparent; font-weight: bold;")

    def initiate_handshake(self):
        current_item = self.peer_list_widget.currentItem()
        if not current_item: return
        
        alias = current_item.text()
        peers = load_peers(self.username, self.fernet)
        peer_data = peers.get(alias)
        peer_gid = peer_data["ghost_id"]
        recipient_sync_hex = peer_data.get("public_key")

        # 1. Target IP Selection
        target_ip = self.manual_ip_input.text().strip() # User typed it in
        if not target_ip:
            target_ip = self.network.discovered_peers.get(peer_gid) # Check WiFi

        if not target_ip:
            QMessageBox.warning(self, "Peer Not Found", "Enter a Target IP for global sync or ensure peer is on same WiFi.")
            return

        # 2. Start Sync
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        def run_sync_thread():
            files_to_send = []
            for i in range(self.project_container.count()):
                cb = self.project_container.itemAt(i).widget()
                if isinstance(cb, QCheckBox) and cb.isChecked():
                    file_name = f"{cb.text().replace(' ', '_')}.enc"
                    file_path = os.path.join(EVERYTHING_ELSE, "projects", self.username, file_name)
                    if os.path.exists(file_path):
                        files_to_send.append(file_path)

            for path in files_to_send:
                self.network.send_file(target_ip, path, recipient_sync_hex, 
                                     progress_callback=self.update_progress_safe)
            
            # Reset UI when done
            self.progress_bar.hide()

        threading.Thread(target=run_sync_thread, daemon=True).start()

    def update_progress_safe(self, value):
        # PySide is picky about threads, this ensures the UI updates correctly
        self.progress_bar.setValue(value)

    def add_peer_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Authorize New Peer")
        dialog.setFixedWidth(400)
        layout = QVBoxLayout(dialog)
        
        name_in = QLineEdit(); name_in.setPlaceholderText("Alias (e.g., Ryan's Laptop)")
        id_in = QLineEdit(); id_in.setPlaceholderText("Ghost ID (Node Address)")
        key_in = QLineEdit(); key_in.setPlaceholderText("Sync Hex (X25519 Key)")
        
        layout.addWidget(QLabel("Alias:")); layout.addWidget(name_in)
        layout.addWidget(QLabel("Ghost ID:")); layout.addWidget(id_in)
        layout.addWidget(QLabel("Public Sync Hex:")); layout.addWidget(key_in)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept); btns.rejected.connect(dialog.reject)
        layout.addWidget(btns)
        
        if dialog.exec() == QDialog.Accepted:
            if name_in.text() and id_in.text() and key_in.text():
                save_peer(self.username, name_in.text().strip(), id_in.text().strip(), key_in.text().strip(), self.fernet)
                self.refresh_peer_list()

    def refresh_peer_list(self):
        self.peer_list_widget.clear()
        peers = load_peers(self.username, self.fernet)
        for alias in peers.keys():
            self.peer_list_widget.addItem(QListWidgetItem(alias))

    def create_clean_asset_group(self, title, container_name):
        group_widget = QWidget()
        layout = QVBoxLayout(group_widget)
        header_row = QHBoxLayout()
        header_label = QLabel(title)
        header_label.setStyleSheet(f"font-weight: bold; color: {COLOR_PROTOCOL}; font-size: 11px;")
        select_all = QPushButton("Select All")
        select_all.setFlat(True)
        select_all.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 11px; text-decoration: underline;")
        header_row.addWidget(header_label); header_row.addStretch(); header_row.addWidget(select_all)
        layout.addLayout(header_row)
        container = QVBoxLayout(); layout.addLayout(container)
        setattr(self, container_name, container)
        select_all.clicked.connect(lambda: self.toggle_selection(container))
        return group_widget

    def toggle_selection(self, container):
        if container.count() == 0: return
        state = not container.itemAt(0).widget().isChecked()
        for i in range(container.count()):
            cb = container.itemAt(i).widget()
            if isinstance(cb, QCheckBox): cb.setChecked(state)

    def populate_assets(self, container, subfolder, filter_ext=False):
        while container.count():
            item = container.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        path = os.path.join(EVERYTHING_ELSE, subfolder, self.username)
        if not os.path.exists(path): return
        for item in os.listdir(path):
            if filter_ext and not item.endswith(('.enc', '.csv', '.json')): continue
            cb = QCheckBox(item)
            cb.setStyleSheet(f"padding: 8px; border: 1px solid {COLOR_BORDER}; border-radius: 4px; background: {COLOR_BG}; color: {COLOR_FG};")
            container.addWidget(cb)

    def display_peer_details(self, index):
        if index == -1:
            self.right_stack.setCurrentIndex(0)
            return
        self.right_stack.setCurrentIndex(1)
        self.peer_title.setText(f"CONFIGURING: {self.peer_list_widget.currentItem().text()}")
        self.populate_assets(self.project_container, "projects")
        self.populate_assets(self.inventory_container, "inventory", filter_ext=True)

    def delete_selected_peer(self):
        current = self.peer_list_widget.currentItem()
        if current and delete_peer(self.username, current.text(), self.fernet):
            self.refresh_peer_list()
            self.right_stack.setCurrentIndex(0)

    def copy_id(self):
        QApplication.clipboard().setText(self.ghost_id)