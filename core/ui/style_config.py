import os
from PySide6.QtGui import QIcon

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

# 1. Initialize the active theme dictionary
T = THEMES[CURRENT_THEME]
T['BG_GLASS'] = "rgba(255, 255, 255, 0.03)"

# 2. DEFINE GLOBAL CONSTANTS (This fixes the 'NameError' in ChatPage)
# These MUST be defined at the top level of the script
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

# 3. LEGACY STYLE STRINGS
STYLE_LABEL = f"color: {COLOR_FG}; font-family: '{FONT_MAIN}'; font-size: 14px;"

# --- ENHANCED UI CONSTANTS ---
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
    QPushButton:hover {{
        background: {T['ACCENT_SOLID']};
    }}
    QPushButton:focus {{
        border: 2px solid #ffffff;
    }}
    QPushButton:pressed {{
        background: {T['BG_PANEL']};
        padding-top: 14px;
    }}
    QPushButton#SecondaryBtn {{
        background: transparent;
        color: {T['TEXT_DIM']};
        border: 1px solid {COLOR_BORDER};
    }}
    QPushButton#SecondaryBtn:hover {{
        color: {COLOR_FG};
        border: 1px solid {COLOR_ACCENT};
    }}
"""

# --- SHARED STYLES ---
STYLE_SCROLLBAR = f"""
    QScrollBar:vertical {{ border: none; background: transparent; width: 6px; }}
    QScrollBar::handle:vertical {{ background: {COLOR_BORDER}; border-radius: 3px; }}
    QScrollBar:horizontal {{ border: none; background: transparent; height: 6px; }}
    QScrollBar::handle:horizontal {{ background: {COLOR_BORDER}; border-radius: 3px; }}
"""

# =====================================================================
# --- MASTER STYLESHEET ---
# =====================================================================

def get_master_stylesheet():
    return f"""
    * {{
        font-family: '{FONT_MAIN}', sans-serif;
        color: {COLOR_FG};
        outline: none;
    }}
    
    /* ADD THE DOT BEFORE QWIDGET */
    QMainWindow, .QWidget {{ 
        background-color: {COLOR_BG};
    }}
    
    /* FORCE SCROLL AREAS TO BE GHOSTS */
    QScrollArea, QScrollArea > QWidget > QWidget {{
        background: transparent !important;
        background-color: transparent !important;
        border: none;
    }}

    QFrame#Sidebar {{
        background-color: {COLOR_BUTTON};
        border-right: 1px solid {COLOR_BORDER};
    }}
    QLabel#LogoLabel {{
        color: {COLOR_ACCENT}; 
        font-size: 18px;
        font-weight: 900;
        letter-spacing: 2px;
        background: transparent;
        padding: 30px 10px 15px 20px;
    }}
    QPushButton#NavButton {{
        background: transparent;
        color: {T['TEXT_DIM']};
        border: none;
        border-radius: 8px;
        text-align: left;
        padding: 12px 20px;
        margin: 2px 12px;
    }}
    QPushButton#NavButton:hover {{ background-color: {COLOR_HIGHLIGHT}; }}
    QPushButton#NavButton:checked {{
        background-color: {T['ACCENT_GLOW']};
        color: {COLOR_ACCENT};
        font-weight: bold;
    }}
    QPushButton#UploadBtn, QPushButton#MainActionBtn, QPushButton[style="primary"] {{
        background: {T['ACCENT']};
        color: #ffffff;
        border-radius: 18px;
        font-weight: 800;
        min-height: 36px;
        padding: 0px 25px;
    }}
    QFrame#FolderCard, QFrame#FileCard {{
        background-color: {T['BG_CARD']};
        border: 1px solid {COLOR_BORDER};
        border-radius: 14px;
    }}
    QFrame#UserCard {{
        background-color: rgba(255, 255, 255, 0.02);
        border: 1px solid {COLOR_BORDER};
        border-radius: 12px;
        margin: 15px;
        padding: 8px;
    }}
    QProgressBar#StorageBar {{
        border: none;
        background-color: rgba(255, 255, 255, 0.05);
        height: 4px;
        border-radius: 2px;
        text-align: center;
    }}
    QProgressBar#StorageBar::chunk {{
        background-color: {COLOR_ACCENT};
        border-radius: 2px;
    }}
    """

def get_main_stylesheet(theme_dict=None): return get_master_stylesheet()

def get_icon(name):
    # Dynamically find the assets folder relative to this file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "..", "Everything_else", f"{name}_icon.png")
    if os.path.exists(icon_path):
        return QIcon(icon_path)
    return QIcon()