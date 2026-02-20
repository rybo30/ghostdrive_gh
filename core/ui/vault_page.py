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
    T, FONT_MAIN, FONT_SIZE, STYLE_BUTTON, STYLE_INPUT
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
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.layout.setSpacing(15)

        # 2. SEARCH & ADD
        top_bar = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search vault entries...")
        self.search_bar.setFixedHeight(40)
        self.search_bar.setStyleSheet(STYLE_INPUT)
        
        self.add_btn = QPushButton("+ New Entry")
        self.add_btn.setFixedSize(140, 40)
        self.add_btn.setStyleSheet(STYLE_BUTTON)
        self.add_btn.clicked.connect(self.add_secret_ui)
        
        top_bar.addWidget(self.search_bar)
        top_bar.addWidget(self.add_btn)
        self.layout.addLayout(top_bar)

        # 3. VAULT LIST
        self.secret_list = QListWidget()
        self.secret_list.itemDoubleClicked.connect(self.show_secret_popup)
        self.secret_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {T['BG_CARD']};
                border: 1px solid {T['BORDER']};
                border-radius: 12px;
                color: {T['TEXT_MAIN']};
                padding: 5px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 16px;
                border-bottom: 1px solid {T['BORDER']};
                font-family: '{FONT_MAIN}';
            }}
            QListWidget::item:selected {{
                background-color: {T['ACCENT_GLOW']};
                color: {T['ACCENT_SOLID']};
                font-weight: bold;
                border-radius: 8px;
            }}
        """)
        self.layout.addWidget(self.secret_list)

        # 4. Footer Controls
        footer = QHBoxLayout()
        self.edit_btn = QPushButton("Edit Entry")
        self.del_btn = QPushButton("Delete")
        
        for btn in [self.edit_btn, self.del_btn]:
            btn.setStyleSheet(STYLE_BUTTON)
            btn.setFixedHeight(38)
            footer.addWidget(btn)
            
        self.edit_btn.clicked.connect(self.edit_selected)
        self.del_btn.clicked.connect(self.delete_selected)
        self.layout.addLayout(footer)

        self.refresh_vault()
        self.search_bar.textChanged.connect(self.filter_secrets)

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
        u_val = data.get("username", "N/A") if isinstance(data, dict) else "[Legacy]"
        p_val = data.get("password", "N/A") if isinstance(data, dict) else str(data)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Vault Entry: {secret_name}")
        dialog.setFixedWidth(450)
        dialog.setStyleSheet(f"background-color: {T['BG_DEEP']}; color: {T['TEXT_MAIN']};")
        
        v_layout = QVBoxLayout(dialog)
        v_layout.setContentsMargins(20, 20, 20, 20)
        v_layout.setSpacing(10)
        
        v_layout.addWidget(QLabel("<b>USERNAME</b>"))
        u_field = QLineEdit(u_val)
        u_field.setReadOnly(True)
        u_field.setStyleSheet(STYLE_INPUT)
        v_layout.addWidget(u_field)

        v_layout.addWidget(QLabel("<b>PASSWORD</b>"))
        p_field = QLineEdit(p_val)
        p_field.setEchoMode(QLineEdit.Password)
        p_field.setReadOnly(True)
        p_field.setStyleSheet(STYLE_INPUT)
        v_layout.addWidget(p_field)

        h_buttons = QHBoxLayout()
        show_btn = QPushButton("Show Password")
        show_btn.setStyleSheet(STYLE_BUTTON)
        def toggle():
            p_field.setEchoMode(QLineEdit.Normal if p_field.echoMode() == QLineEdit.Password else QLineEdit.Password)
            show_btn.setText("Hide Password" if p_field.echoMode() == QLineEdit.Normal else "Show Password")
        show_btn.clicked.connect(toggle)
        
        copy_btn = QPushButton("Copy")
        copy_btn.setStyleSheet(STYLE_BUTTON)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(p_field.text()))

        h_buttons.addWidget(show_btn)
        h_buttons.addWidget(copy_btn)
        v_layout.addLayout(h_buttons)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(STYLE_BUTTON)
        close_btn.clicked.connect(dialog.accept)
        v_layout.addWidget(close_btn)
        dialog.exec()

    def add_secret_ui(self):
        name, ok1 = QInputDialog.getText(self, "Add Entry", "System/Site Name:")
        if not ok1 or not name: return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"New Credentials: {name}")
        dialog.setStyleSheet(f"background-color: {T['BG_DEEP']}; color: {T['TEXT_MAIN']};")
        v_layout = QVBoxLayout(dialog)

        v_layout.addWidget(QLabel("Username:"))
        u_input = QLineEdit()
        u_input.setStyleSheet(STYLE_INPUT)
        v_layout.addWidget(u_input)

        v_layout.addWidget(QLabel("Password:"))
        p_input = QLineEdit()
        p_input.setStyleSheet(STYLE_INPUT)
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
        u_init = raw_data.get("username", "") if isinstance(raw_data, dict) else ""
        p_init = raw_data.get("password", "") if isinstance(raw_data, dict) else str(raw_data)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit: {old_name}")
        dialog.setStyleSheet(f"background-color: {T['BG_DEEP']}; color: {T['TEXT_MAIN']};")
        v_layout = QVBoxLayout(dialog)

        v_layout.addWidget(QLabel("Username:"))
        u_input = QLineEdit(u_init)
        u_input.setStyleSheet(STYLE_INPUT)
        v_layout.addWidget(u_input)

        v_layout.addWidget(QLabel("Password:"))
        p_input = QLineEdit(p_init)
        p_input.setStyleSheet(STYLE_INPUT)
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
        if QMessageBox.question(self, "Delete", f"Delete {name}?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                delete_secret(self.username, self.passphrase, name)
                self.refresh_vault()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def generate_password_suggestion(self) -> str:
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(random.choices(chars, k=random.randint(14, 18)))