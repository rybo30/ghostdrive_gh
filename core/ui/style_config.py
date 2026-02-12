import os
from PySide6.QtGui import QColor, QIcon

# --- Core Settings ---
FONT_FAMILY = "Segoe UI"
FONT_SIZE = 11

# --- Standalone Variables ---
COLOR_BG = "#fefefe"
COLOR_FG = "#111111"
COLOR_ACCENT = "#62b5e5"
COLOR_BUTTON = "#e2f1fb"
COLOR_HIGHLIGHT = "#b1e0ff"
COLOR_PAGE_BG = "#eaf6ff"
COLOR_PROTOCOL = "#B8860B"
COLOR_BORDER = "#d1d1d1"

# --- RESTORED LEGACY VARIABLES ---
STYLE_LABEL = f"color: {COLOR_FG}; font-family: '{FONT_FAMILY}'; font-size: {FONT_SIZE}px;"

# Note: The CSS below is flushed to the left to avoid indentation bugs in Python
STYLE_BUTTON = f"""
QPushButton {{
    border: 1px solid {COLOR_ACCENT};
    border-radius: 5px;
    padding: 8px;
    background-color: {COLOR_BUTTON};
    color: {COLOR_FG};
    outline: none;
}}

QPushButton:focus {{
    background-color: {COLOR_HIGHLIGHT};
    border: 2px solid {COLOR_ACCENT};
}}

QPushButton:hover {{
    background-color: {COLOR_ACCENT};
    color: white;
}}
"""

# --- Icon Logic ---
def get_viking_icon():
    icon_path = os.path.join(os.path.dirname(__file__), "..", "Everything_else", "viking_icon.png")
    if os.path.exists(icon_path):
        return QIcon(icon_path)
    return QIcon()

# --- Dynamic Theme Helper ---
def get_main_stylesheet(theme):
    """Generates the master CSS based on the user's custom theme dictionary."""
    bg = theme.get('COLOR_BG', COLOR_BG)
    fg = theme.get('COLOR_FG', COLOR_FG)
    accent = theme.get('COLOR_ACCENT', COLOR_ACCENT)
    
    return f"""
QMainWindow, QWidget {{
    background-color: {bg};
    color: {fg};
    font-family: '{FONT_FAMILY}';
}}
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 8px;
}}
QScrollBar::handle:vertical {{
    background: {accent};
    min-height: 30px;
    border-radius: 4px;
}}
"""