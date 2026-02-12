import random
import string
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel,
    QListWidget, QInputDialog, QMessageBox, QDialog, QHBoxLayout, 
    QApplication, QFrame
)
from PySide6.QtCore import Qt
from Everything_else.ghostvault import add_secret, get_secrets, delete_secret
from .style_config import (
    FONT_FAMILY, FONT_SIZE,
    COLOR_BG, COLOR_FG, COLOR_BORDER, COLOR_ACCENT, COLOR_BUTTON, COLOR_HIGHLIGHT,
    STYLE_BUTTON, COLOR_PAGE_BG
)

class VaultPage(QWidget):
    def __init__(self, username, passphrase, fernet):
        super().__init__()
        self.username = username
        self.passphrase = passphrase
        self.fernet = fernet
        self.secrets = {}

        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(15)

        # 1. Header Section (Matching Project Manager Style)
        header_layout = QVBoxLayout()
        self.header = QLabel("ENCRYPTED PASSWORD VAULT")
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setStyleSheet(f"color: {COLOR_FG}; font-size: {FONT_SIZE + 10}px; font-weight: bold; letter-spacing: 1px; margin-bottom: 5px;")
        header_layout.addWidget(self.header)

        # The Divider Line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {COLOR_ACCENT}; min-height: 2px; max-height: 2px;")
        header_layout.addWidget(line)
        
        # Add the header layout to your main container
        self.layout.addLayout(header_layout)

        # 2. SEARCH & ADD
        top_bar = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search vault entries...")
        self.search_bar.setFixedHeight(35)
        self.search_bar.textChanged.connect(self.filter_secrets)
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_PAGE_BG};
                color: {COLOR_FG};
                border: 1px solid {COLOR_BUTTON};
                border-radius: 4px;
                padding-left: 10px;
            }}
        """)
        
        self.add_btn = QPushButton("+ New Entry")
        self.add_btn.setFixedSize(120, 35)
        self.add_btn.setStyleSheet(STYLE_BUTTON)
        self.add_btn.clicked.connect(self.add_secret_ui)
        
        top_bar.addWidget(self.search_bar)
        top_bar.addWidget(self.add_btn)
        self.layout.addLayout(top_bar)

        # 3. VAULT LIST - Refined for sharp selection
        self.secret_list = QListWidget()
        self.secret_list.itemDoubleClicked.connect(self.show_secret_popup)
        self.secret_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLOR_PAGE_BG};
                border: 1px solid {COLOR_BUTTON};
                border-radius: 4px;
                color: {COLOR_FG};
                outline: none; /* Removes the dotted focus circle */
                padding: 2px;
            }}
            QListWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {COLOR_BG};
                margin: 0px;
            }}
            QListWidget::item:selected {{
                background-color: {COLOR_HIGHLIGHT};
                color: {COLOR_BG};
                border-radius: 0px; /* Sharp edges for a cleaner 'tech' look */
            }}
            QListWidget::item:hover {{
                background-color: {COLOR_HIGHLIGHT};
                color: {COLOR_BG};
                opacity: 0.7;
            }}
        """)
        self.layout.addWidget(self.secret_list)

        # 4. FOOTER CONTROLS
        footer = QHBoxLayout()
        self.edit_btn = QPushButton("Edit Selection")
        self.del_btn = QPushButton("Delete Entry")
        
        for btn in [self.edit_btn, self.del_btn]:
            btn.setStyleSheet(STYLE_BUTTON)
            btn.setFixedHeight(35)
            footer.addWidget(btn)
            
        self.edit_btn.clicked.connect(self.edit_selected)
        self.del_btn.clicked.connect(self.delete_selected)
        self.layout.addLayout(footer)

        self.refresh_vault()

    def refresh_vault(self):
        self.secret_list.clear()
        try:
            self.secrets = get_secrets(self.username, self.passphrase)
            for name in sorted(self.secrets.keys(), key=str.lower):
                self.secret_list.addItem(name)
        except Exception as e:
            QMessageBox.critical(self, "Vault Error", str(e))

    def filter_secrets(self, text):
        self.secret_list.clear()
        filtered = [n for n in sorted(self.secrets.keys(), key=str.lower)
                    if text.lower() in n.lower()]
        for name in filtered:
            self.secret_list.addItem(name)

    def show_secret_popup(self, item):
        secret_name = item.text()
        data = self.secrets.get(secret_name, {})

        # Hybrid Fix for Old Passwords
        if isinstance(data, dict):
            u_val = data.get("username", "N/A")
            p_val = data.get("password", "N/A")
        else:
            u_val = "[Legacy No Username]"
            p_val = str(data)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Vault Entry: {secret_name}")
        dialog.setFixedWidth(450) # Widened slightly for text buttons
        dialog.setStyleSheet(f"background-color: {COLOR_BG}; color: {COLOR_FG};")
        
        v_layout = QVBoxLayout(dialog)
        v_layout.setContentsMargins(20, 20, 20, 20)
        v_layout.setSpacing(10)
        
        # Username Section
        v_layout.addWidget(QLabel("<b>USERNAME</b>"))
        u_field = QLineEdit(u_val)
        u_field.setReadOnly(True)
        u_field.setStyleSheet(f"background: {COLOR_PAGE_BG}; color: {COLOR_FG}; border: 1px solid {COLOR_BUTTON}; padding: 8px;")
        v_layout.addWidget(u_field)

        # Password Section
        v_layout.addWidget(QLabel("<b>PASSWORD</b>"))
        p_field = QLineEdit(p_val)
        p_field.setEchoMode(QLineEdit.Password)
        p_field.setReadOnly(True)
        p_field.setStyleSheet(f"background: {COLOR_PAGE_BG}; color: {COLOR_FG}; border: 1px solid {COLOR_BUTTON}; padding: 8px;")
        v_layout.addWidget(p_field)

        # Action Buttons Row
        h_buttons = QHBoxLayout()
        
        show_btn = QPushButton("Show Password")
        show_btn.setFixedHeight(35)
        show_btn.setStyleSheet(STYLE_BUTTON)
        # Simple toggle logic for the text and masking
        def toggle_password():
            if p_field.echoMode() == QLineEdit.Password:
                p_field.setEchoMode(QLineEdit.Normal)
                show_btn.setText("Hide Password")
            else:
                p_field.setEchoMode(QLineEdit.Password)
                show_btn.setText("Show Password")
                
        show_btn.clicked.connect(toggle_password)
        
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.setFixedHeight(35)
        copy_btn.setStyleSheet(STYLE_BUTTON)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(p_field.text()))

        h_buttons.addWidget(show_btn)
        h_buttons.addWidget(copy_btn)
        v_layout.addLayout(h_buttons)

        # Close Button
        v_layout.addSpacing(10)
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(STYLE_BUTTON)
        close_btn.setFixedHeight(35)
        close_btn.clicked.connect(dialog.accept)
        v_layout.addWidget(close_btn)
        
        dialog.exec()

    def add_secret_ui(self):
        name, ok1 = QInputDialog.getText(self, "Add Entry", "System/Site Name:")
        if not ok1 or not name: return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"New Credentials: {name}")
        dialog.setStyleSheet(f"background-color: {COLOR_BG}; color: {COLOR_FG};")
        v_layout = QVBoxLayout(dialog)

        v_layout.addWidget(QLabel("Username:"))
        u_input = QLineEdit()
        u_input.setStyleSheet(f"background: {COLOR_PAGE_BG}; color: {COLOR_FG}; border: 1px solid {COLOR_BUTTON}; padding: 8px;")
        v_layout.addWidget(u_input)

        v_layout.addWidget(QLabel("Password:"))
        p_input = QLineEdit()
        p_input.setStyleSheet(f"background: {COLOR_PAGE_BG}; color: {COLOR_FG}; border: 1px solid {COLOR_BUTTON}; padding: 8px;")
        v_layout.addWidget(p_input)

        gen_btn = QPushButton("🤖 Suggest Strong Password")
        gen_btn.setStyleSheet(STYLE_BUTTON)
        gen_btn.clicked.connect(lambda: p_input.setText(self.generate_password_suggestion()))
        v_layout.addWidget(gen_btn)

        save_btn = QPushButton("Save Entry")
        save_btn.setStyleSheet(STYLE_BUTTON)
        save_btn.clicked.connect(dialog.accept)
        v_layout.addWidget(save_btn)

        if dialog.exec() == QDialog.Accepted:
            try:
                add_secret(self.username, self.passphrase, name, u_input.text(), p_input.text())
                self.refresh_vault()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def edit_selected(self):
        selected = self.secret_list.currentItem()
        if not selected: return
        
        old_name = selected.text()
        raw_data = self.secrets.get(old_name, "")

        # Hybrid fix for pre-population
        if isinstance(raw_data, dict):
            u_init, p_init = raw_data.get("username", ""), raw_data.get("password", "")
        else:
            u_init, p_init = "", str(raw_data)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit: {old_name}")
        dialog.setStyleSheet(f"background-color: {COLOR_BG}; color: {COLOR_FG};")
        v_layout = QVBoxLayout(dialog)

        v_layout.addWidget(QLabel("Username:"))
        u_input = QLineEdit(u_init)
        u_input.setStyleSheet(f"background: {COLOR_PAGE_BG}; color: {COLOR_FG}; border: 1px solid {COLOR_BUTTON}; padding: 8px;")
        v_layout.addWidget(u_input)

        v_layout.addWidget(QLabel("Password:"))
        p_input = QLineEdit(p_init)
        p_input.setStyleSheet(f"background: {COLOR_PAGE_BG}; color: {COLOR_FG}; border: 1px solid {COLOR_BUTTON}; padding: 8px;")
        v_layout.addWidget(p_input)

        save_btn = QPushButton("Update Entry")
        save_btn.setStyleSheet(STYLE_BUTTON)
        save_btn.clicked.connect(dialog.accept)
        v_layout.addWidget(save_btn)

        if dialog.exec() == QDialog.Accepted:
            try:
                delete_secret(self.username, self.passphrase, old_name)
                add_secret(self.username, self.passphrase, old_name, u_input.text(), p_input.text())
                self.refresh_vault()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_selected(self):
        selected = self.secret_list.currentItem()
        if not selected: return
        name = selected.text()
        
        if QMessageBox.question(self, "Delete", f"Are you sure you want to delete {name}?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                delete_secret(self.username, self.passphrase, name)
                self.refresh_vault()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def generate_password_suggestion(self) -> str:
        length = random.randint(14, 18)
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(random.choices(chars, k=length))