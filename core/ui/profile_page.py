import json, os, time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QLabel, QPushButton, 
    QFormLayout, QFrame, QHBoxLayout, QScrollArea, QMessageBox, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QTimer
from .style_config import (
    COLOR_FG, COLOR_ACCENT, STYLE_BUTTON, T
)

# --- PORTABLE PATH IMPORTS ---
from core.paths import USER_DATA, PROJECTS_DIR, INVENTORY_DIR, CORE_DIR, MODELS_DIR

# --- LOGIC IMPORTS ---
from Everything_else.ghostvault import get_secrets
from project_manager import list_project_files
from Everything_else.inventory_manager import list_inventory_sheets
from core.peers_manager import load_peers

# System Protocols
from core.system_protocols import (
    get_disk_status, get_battery_status, get_primary_ip, get_system_uptime
)

class ProfilePage(QWidget):
    profile_updated = Signal()

    def __init__(self, username, fernet, passphrase=None): 
        super().__init__()
        self.username = username
        self.fernet = fernet
        self.passphrase = passphrase
        
        # Portable Pathing
        self.profile_path = os.path.join(USER_DATA, f"{username}_profile.enc")
        
        self.setup_ui()
        self.load_profile()  
        self.refresh_stats() 
        
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_live_metrics)
        self.refresh_timer.start(3000)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(20)

        # 1. Header
        header_row = QHBoxLayout()
        self.title_label = QLabel("NEURAL INTERFACE: OPERATOR OVERVIEW")
        self.title_label.setStyleSheet(f"color: {COLOR_FG}; font-size: 18px; font-weight: 800; letter-spacing: 2px;")
        
        self.uptime_label = QLabel("UPTIME: --")
        self.uptime_label.setStyleSheet(f"color: {COLOR_ACCENT}; font-family: 'Consolas'; font-size: 11px;")
        
        header_row.addWidget(self.title_label)
        header_row.addStretch()
        header_row.addWidget(self.uptime_label)
        main_layout.addLayout(header_row)

        # 2. Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content_widget = QWidget()
        self.content_vbox = QVBoxLayout(content_widget)
        self.content_vbox.setSpacing(25)

        # --- SECTION A: SYSTEM HUD ---
        self.hud_card = QFrame()
        self.hud_card.setStyleSheet("background-color: #141d26; border: 1px solid #2c3e50; border-radius: 10px;")
        hud_layout = QGridLayout(self.hud_card)
        hud_layout.setContentsMargins(20, 20, 20, 20)
        hud_layout.setHorizontalSpacing(40)
        hud_layout.setVerticalSpacing(15)
        
        self.stat_labels = {}
        metrics = [
            ("Vault Files", "vault_count", 0, 0),
            ("AI Models", "pass_count", 0, 1),
            ("Active Missions", "proj_count", 0, 2),
            ("Intel Sheets", "inv_count", 0, 3),
            ("Trusted Network", "net_count", 1, 0),
            ("Computer Storage", "disk", 1, 1),
            ("Computer Battery", "batt", 1, 2),
            ("Local IP", "ip", 1, 3)
        ]

        for name, key, r, c in metrics:
            vbox = QVBoxLayout()
            vbox.setSpacing(2)
            t_lbl = QLabel(name.upper())
            t_lbl.setStyleSheet("color: #7f8c8d; font-size: 9px; border: none; font-weight: bold;")
            v_lbl = QLabel("0")
            v_lbl.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 14px; font-weight: bold; font-family: 'Consolas'; border: none;")
            vbox.addWidget(t_lbl)
            vbox.addWidget(v_lbl)
            self.stat_labels[key] = v_lbl
            hud_layout.addLayout(vbox, r, c)

        self.content_vbox.addWidget(self.hud_card)

        # --- SECTION B: OPERATOR HEURISTICS ---
        self.master_card = QFrame()
        self.master_card.setStyleSheet("background-color: #1c2833; border-radius: 12px; border: 1px solid #34495e;")
        card_layout = QVBoxLayout(self.master_card)
        card_layout.setContentsMargins(25, 25, 25, 25)

        ident_label = QLabel("OPERATOR PERSONALITY & COGNITIVE MAPPING")
        ident_label.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 11px; font-weight: bold; letter-spacing: 1px; border: none;")
        card_layout.addWidget(ident_label)
        card_layout.addSpacing(10)

        h_form = QFormLayout()
        input_style = "border: 1px solid #34495e; border-radius: 6px; padding: 10px; background: #2c3e50; color: white; font-size: 13px;"
        
        self.h_inputs = {}
        questions = [
            ("callsign", "Callsign"), 
            ("region", "Current Region"),
            ("goal", "Primary Objective"), 
            ("fear", "Critical Fear"),
            ("logic", "Data Processing Style")
        ]
        
        for key, label_text in questions:
            self.h_inputs[key] = QLineEdit()
            w = self.h_inputs[key]
            w.setPlaceholderText(f"Establish {label_text.lower()}...")
            w.setStyleSheet(input_style)
            label = QLabel(label_text.upper())
            label.setStyleSheet("color: #7f8c8d; font-size: 10px; border: none;")
            h_form.addRow(label, w)
        
        card_layout.addLayout(h_form)
        self.content_vbox.addWidget(self.master_card)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        footer = QHBoxLayout()
        self.save_btn = QPushButton("INITIALIZE COMMIT")
        self.save_btn.setFixedSize(220, 45)
        self.save_btn.setStyleSheet(STYLE_BUTTON + "font-size: 12px; font-weight: bold;")
        self.save_btn.clicked.connect(self.save_profile)
        
        footer.addStretch()
        footer.addWidget(self.save_btn)
        main_layout.addLayout(footer)

    def refresh_live_metrics(self):
        try:
            # System Protocols
            disk = get_disk_status()
            if "disk" in self.stat_labels:
                self.stat_labels["disk"].setText(f"{disk.get('percent_used', 0)}% USED")
            
            batt_info = get_battery_status()
            batt_val = batt_info.split("(")[0].strip() if batt_info else "N/A"
            if "batt" in self.stat_labels:
                self.stat_labels["batt"].setText(batt_val)
            
            if "ip" in self.stat_labels:
                self.stat_labels["ip"].setText(get_primary_ip())
                
            self.uptime_label.setText(f"UPTIME: {get_system_uptime().upper()}")
        except Exception as e: 
            # This will now print the SPECIFIC reason it's failing if it happens again
            print(f"HUD Live Refresh Error: {e}")

    def refresh_stats(self):
        try:
            # 1. Vault Files (STRICTLY .DAT - UNTOUCHED)
            if os.path.exists(USER_DATA):
                v_files = [f for f in os.listdir(USER_DATA) 
                          if f.endswith('.dat') and os.path.isfile(os.path.join(USER_DATA, f))]
                self.stat_labels["vault_count"].setText(str(len(v_files)))
            
            # 2. AI Models (.gguf count - WITH GHOST FILE FILTER)
            if not os.path.exists(MODELS_DIR):
                os.makedirs(MODELS_DIR, exist_ok=True)
            
            # FILTER: Must end in .gguf AND not start with '.' AND must be over 1MB
            m_files = []
            for f in os.listdir(MODELS_DIR):
                f_path = os.path.join(MODELS_DIR, f)
                if f.lower().endswith('.gguf') and not f.startswith('.') and os.path.isfile(f_path):
                    # Final safety check: skip files that are effectively empty (under 1KB)
                    if os.path.getsize(f_path) > 1024: 
                        m_files.append(f)
            
            self.stat_labels["pass_count"].setText(str(len(m_files)))

            # 3. Projects
            proj_list = list_project_files(self.username)
            self.stat_labels["proj_count"].setText(str(len(proj_list)))

            # 4. Inventory
            sheets = list_inventory_sheets(self.username)
            self.stat_labels["inv_count"].setText(str(len(sheets)))

            # 5. Nodes
            peers = load_peers(self.username, self.fernet)
            self.stat_labels["net_count"].setText(str(len(peers)))

        except Exception as e:
            print(f"DEBUG Stats Error: {e}")

    def save_profile(self):
        data = {"heuristics": {k: w.text() for k, w in self.h_inputs.items()}}
        try:
            raw_json = json.dumps(data).encode()
            encrypted = self.fernet.encrypt(raw_json)
            with open(self.profile_path, "wb") as f:
                f.write(encrypted)
            
            self.save_btn.setText("SYNC COMPLETE")
            self.refresh_stats()
            self.profile_updated.emit()
            QTimer.singleShot(2000, lambda: self.save_btn.setText("INITIALIZE COMMIT"))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Link Failed: {e}")

    def load_profile(self):
        if not os.path.exists(self.profile_path): return
        try:
            with open(self.profile_path, "rb") as f:
                decrypted = self.fernet.decrypt(f.read())
                data = json.loads(decrypted)
                heur = data.get("heuristics", {})
                for k, w in self.h_inputs.items():
                    w.setText(heur.get(k, ""))
        except Exception as e:
            print(f"DEBUG Load Error: {e}")