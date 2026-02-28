import os
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QFrame, QLineEdit, QTextEdit, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QPoint

# --- THEME SELECTION ---
CURRENT_THEME = "GHOST_DARK"

THEMES = {
    "GHOST_DARK": {
        "BG_DEEP": "#0d1117",
        "BG_PANEL": "#161b22",
        "BG_CARD": "rgba(33, 38, 45, 0.4)",
        "BG_HOVER": "rgba(88, 166, 255, 0.08)",
        "ACCENT": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #58a6ff, stop:1 #1f6feb)",
        "ACCENT_SOLID": "#58a6ff",
        "ACCENT_GLOW": "rgba(88, 166, 255, 0.12)",
        "TEXT_MAIN": "#c9d1d9",
        "TEXT_DIM": "#8b949e",
        "BORDER": "rgba(48, 54, 61, 0.6)",
        "SUCCESS": "#238636",
        "DANGER": "#da3633",
    }
}

T = THEMES[CURRENT_THEME]
T['BG_GLASS'] = "rgba(255, 255, 255, 0.03)"
T['PROTOCOL_GOLD'] = "#ffb000"
T['PROTOCOL_BG'] = "rgba(13, 17, 23, 0.95)"
T['HUD_LINE'] = "rgba(88, 166, 255, 0.3)"

# --- GLOBAL CONSTANTS (Restoring what was lost) ---
COLOR_BG = T['BG_DEEP']
COLOR_FG = T['TEXT_MAIN']
COLOR_ACCENT = T['ACCENT_SOLID']
COLOR_BUTTON = T['BG_PANEL']
COLOR_HIGHLIGHT = T['BG_HOVER']
COLOR_BORDER = T['BORDER']
COLOR_PROTOCOL = T['ACCENT_SOLID'] 
COLOR_PAGE_BG = T['BG_PANEL']
FONT_MAIN = "Segoe UI" if os.name == "nt" else "Inter"
FONT_FAMILY = FONT_MAIN
FONT_SIZE = 14
COLOR_CARD_DARK = "#0d1117"
COLOR_CARD_MED = "#1c2833"
COLOR_TEXT_DIM = T['TEXT_DIM']
COLOR_MANUAL_BORDER = T['BORDER']

# --- RESTORED STYLE STRINGS ---
STYLE_SECTION_TITLE = f"color: {COLOR_ACCENT}; font-size: 14px; font-weight: 800; letter-spacing: 2px; border: none;"
STYLE_HUD_VAL = f"color: {COLOR_ACCENT}; font-size: 18px; font-weight: bold; font-family: 'Consolas'; border: none;"
STYLE_HUD_LBL = f"color: {COLOR_TEXT_DIM}; font-size: 10px; border: none; font-weight: bold;"
STYLE_LABEL = f"color: {COLOR_FG}; font-family: '{FONT_MAIN}'; font-size: 14px;"

STYLE_HEURISTIC_INPUT = f"""
    QLineEdit {{
        background-color: rgba(13, 17, 23, 0.6);
        color: {COLOR_FG};
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 12px;
        font-size: 13px;
    }}
"""

STYLE_CARD_MANUAL = f"QFrame {{ background-color: {COLOR_CARD_DARK}; border: 1px solid {COLOR_MANUAL_BORDER}; border-radius: 12px; }}"
STYLE_CARD_HEURISTIC = f"QFrame {{ background-color: {COLOR_CARD_MED}; border: 1px solid #34495e; border-radius: 12px; }}"

STYLE_INPUT = f"""
    QLineEdit {{
        background-color: #0d1117;
        color: {COLOR_FG};
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        padding: 10px;
    }}
    QLineEdit:focus {{
        border: 1px solid {COLOR_ACCENT};
        background-color: #121d2f;
    }}
"""

STYLE_BUTTON = f"""
    QPushButton {{
        background: {T['ACCENT']};
        color: white;
        border-radius: 18px;
        font-weight: 800;
        padding: 12px;
        outline: none;
    }}
    QPushButton:hover {{ background: {T['ACCENT_SOLID']}; }}
    QPushButton#SecondaryBtn {{
        background: transparent;
        color: {T['TEXT_DIM']};
        border: 1px solid {COLOR_BORDER};
    }}
"""

STYLE_SCROLLBAR = f"""
    QScrollBar:vertical {{ border: none; background: transparent; width: 6px; }}
    QScrollBar::handle:vertical {{ background: {COLOR_BORDER}; border-radius: 3px; }}
"""

# --- DIALOG CLASSES ---
class TacticalDialog(QDialog):
    def __init__(self, parent=None, title="SYSTEM COMMAND", label="INPUT:", placeholder="...", is_password=False, is_multiline=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setFixedWidth(450)
        self._drag_pos = QPoint()

        GOLD = T['PROTOCOL_GOLD']
        BG = T['PROTOCOL_BG']
        LINE = T['HUD_LINE']
        
        self.container = QFrame(self)
        self.container.setObjectName("ProtocolBox")
        self.container.setStyleSheet(f"QFrame#ProtocolBox {{ background-color: {BG}; border: 2px solid {GOLD}; border-radius: 12px; }}")
        
        layout = QVBoxLayout(self.container)
        
        header = QLabel(title.upper())
        header.setStyleSheet(f"color: {GOLD}; font-weight: 900; letter-spacing: 3px; font-size: 11px; border: none; background: transparent;")
        layout.addWidget(header)
        
        line_frame = QFrame()
        line_frame.setFixedHeight(1)
        line_frame.setStyleSheet(f"background-color: {LINE};")
        layout.addWidget(line_frame)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {GOLD}; font-family: 'Consolas'; font-size: 12px; margin-top: 10px; border: none; background: transparent;")
        layout.addWidget(lbl)

        if is_multiline:
            self.input_field = QTextEdit()
            self.input_field.setMinimumHeight(100)
        else:
            self.input_field = QLineEdit()
            if is_password: self.input_field.setEchoMode(QLineEdit.Password)
        
        self.input_field.setPlaceholderText(placeholder)
        self.input_field.setStyleSheet(f"background: rgba(0,0,0,0.5); color: {GOLD}; border: 1px solid {LINE}; border-radius: 4px; padding: 10px; font-family: 'Consolas'; font-size: 14px;")
        layout.addWidget(self.input_field)

        btn_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("CONFIRM")
        self.cancel_btn = QPushButton("ABORT")
        
        btn_style = f"QPushButton {{ background: transparent; border: 1px solid {LINE}; color: {T['TEXT_DIM']}; padding: 8px; font-weight: bold; border-radius: 4px; }}"
        self.cancel_btn.setStyleSheet(btn_style)
        self.confirm_btn.setStyleSheet(btn_style.replace(T['TEXT_DIM'], GOLD).replace("transparent", "rgba(255,176,0,0.15)"))

        btn_layout.addWidget(self.confirm_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.confirm_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.container)

    def get_value(self):
        if isinstance(self.input_field, QTextEdit): return self.input_field.toPlainText().strip()
        return self.input_field.text().strip()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

# --- HELPERS ---
def ghost_alert(parent, title, message):
    dialog = TacticalDialog(parent, title=title, label=message)
    dialog.input_field.hide() 
    if any(x in title.upper() for x in ["DELETE", "DESTROY", "ERASE", "PURGE", "KILL"]):
        dialog.confirm_btn.setText("TERMINATE")
        dialog.confirm_btn.setStyleSheet(dialog.confirm_btn.styleSheet().replace(T['PROTOCOL_GOLD'], "#ff4444"))
    else:
        dialog.confirm_btn.setText("CONFIRM")
    dialog.confirm_btn.setFocus()
    return dialog.exec() == QDialog.Accepted

def ghost_prompt(parent, title, label, placeholder="...", password=False, multiline=False):
    dialog = TacticalDialog(parent, title, label, placeholder, is_password=password, is_multiline=multiline)
    if dialog.exec() == QDialog.Accepted: return dialog.get_value(), True
    return "", False

def get_master_stylesheet():
    return f"""
    * {{ font-family: '{FONT_MAIN}', sans-serif; color: {COLOR_FG}; outline: none; }}
    QMainWindow, .QWidget {{ background-color: {COLOR_BG}; }}
    QFrame#Sidebar {{ background-color: {COLOR_BUTTON}; border-right: 1px solid {COLOR_BORDER}; }}
    QLabel#LogoLabel {{ color: {COLOR_ACCENT}; font-size: 18px; font-weight: 900; letter-spacing: 2px; background: transparent; padding: 30px 10px 15px 20px; }}
    QPushButton#NavButton {{ background: transparent; color: {T['TEXT_DIM']}; border: none; border-radius: 8px; text-align: left; padding: 12px 20px; margin: 2px 12px; }}
    QPushButton#NavButton:hover {{ background-color: {COLOR_HIGHLIGHT}; }}
    QPushButton#NavButton:checked {{ background-color: {T['ACCENT_GLOW']}; color: {COLOR_ACCENT}; font-weight: bold; }}
    QProgressBar#StorageBar {{ border: none; background-color: rgba(255, 255, 255, 0.05); height: 4px; border-radius: 2px; }}
    QProgressBar#StorageBar::chunk {{ background-color: {COLOR_ACCENT}; border-radius: 2px; }}
    """

def get_main_stylesheet(theme_dict=None): return get_master_stylesheet()

def get_icon(name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "..", "Everything_else", f"{name}_icon.png")
    return QIcon(icon_path) if os.path.exists(icon_path) else QIcon()