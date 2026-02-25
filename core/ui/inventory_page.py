# [inventory_page.py]

import os
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTableWidget, QLineEdit,
    QHBoxLayout, QMessageBox, QDialog, QFormLayout, QTableWidgetItem, 
    QInputDialog, QHeaderView, QLabel, QTabBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from datetime import datetime

# Import the GPS from core.paths
from core.paths import CORE_DIR, EVERYTHING_ELSE, INVENTORY_DIR

# Ensure Everything_else logic can be found
if EVERYTHING_ELSE not in sys.path:
    sys.path.insert(0, EVERYTHING_ELSE)

# Import from manager directly
from inventory_manager import (
    load_inventory, save_inventory, export_inventory_to_csv, import_inventory_from_csv
)

from .style_config import (
    FONT_FAMILY, FONT_SIZE,
    COLOR_BG, COLOR_FG, COLOR_ACCENT, COLOR_BUTTON, COLOR_HIGHLIGHT,
    STYLE_LABEL, STYLE_BUTTON, COLOR_PAGE_BG, COLOR_BORDER, ghost_prompt, ghost_alert, TacticalDialog
)

class InventoryPage(QWidget):
    def __init__(self, username, passphrase, fernet):
        super().__init__()
        self.username = username
        self.passphrase = passphrase
        self.fernet = fernet
        self.current_sheet_name = "inventory" # Track which sheet is active

        # 1. Main Background Styling
        self.setStyleSheet(f"background-color: {COLOR_BG}; color: {COLOR_FG}; font-family: '{FONT_FAMILY}';")
        self.layout = QVBoxLayout(self)

        # 2. Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLOR_BUTTON}; 
                color: {COLOR_FG}; 
                border: 1px solid {COLOR_ACCENT};
                border-radius: 4px;
                padding: 5px;
            }}
        """)
        self.search_bar.textChanged.connect(self.filter_inventory)
        self.layout.addWidget(self.search_bar)

        # --- 🆕 3. TAB BAR SECTION (Multi-Sheet Logic) ---
        tab_container = QHBoxLayout()
        
        self.tabs = QTabBar()
        self.tabs.setExpanding(False)
        self.tabs.setDrawBase(False)
        self.tabs.setStyleSheet(f"""
            QTabBar::tab {{
                background: {COLOR_BUTTON};
                color: {COLOR_FG};
                padding: 8px 15px;
                border: 1px solid {COLOR_BORDER};
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {COLOR_ACCENT};
                color: white;
                font-weight: bold;
            }}
        """)
        self.tabs.currentChanged.connect(self.switch_sheet)
        
        # Add Sheet Button
        self.add_sheet_btn = QPushButton("+")
        self.add_sheet_btn.setFixedWidth(40)
        self.add_sheet_btn.setStyleSheet(STYLE_BUTTON)
        self.add_sheet_btn.clicked.connect(self.create_new_sheet)

        tab_container.addWidget(self.tabs)
        tab_container.addWidget(self.add_sheet_btn)
        tab_container.addStretch() # Pushes everything to the left
        self.layout.addLayout(tab_container)

        # 4. Table Config
        self.table = QTableWidget()
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLOR_PAGE_BG}; 
                color: {COLOR_FG};
                gridline-color: {COLOR_ACCENT};
                border-radius: 4px;
            }}
            QHeaderView::section {{
                background-color: {COLOR_ACCENT};
                color: #000000;  /* Changed from white to black */
                border: 1px solid {COLOR_BG};
                font-weight: bold; /* Optional: adds extra 'pop' against the green */
            }}
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)

        # 5. Action Buttons
        btn_layout = QHBoxLayout()
        for label, func in [
            ("Add Item", self.add_item),
            ("Edit", self.edit_item),
            ("Delete", self.delete_item),
            ("Columns", self.edit_columns),
            ("Rename Sheet", self.rename_current_sheet),
            ("Export", self.export_csv),
            ("Import", self.import_csv)
        ]:
            b = QPushButton(label)
            b.setStyleSheet(STYLE_BUTTON)
            b.clicked.connect(func)
            btn_layout.addWidget(b)

        self.layout.addLayout(btn_layout)

        # 6. INITIAL DATA SETUP (Must happen before loading tabs)
        self.schema = [] 
        self.data = []
        
        # Now it is safe to load the list and the actual data
        self.load_sheet_list() 
        self.refresh_table()

    # --- 🆕 MULTI-SHEET LOGIC ---

    def load_sheet_list(self):
        """Finds all .enc sheets for this user and populates the tab bar."""
        from inventory_manager import list_inventory_sheets
        sheets = list_inventory_sheets(self.username)
        
        self.tabs.blockSignals(True) 
        
        # FIX: QTabBar doesn't have .clear(), so we remove tabs by index
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)
            
        for s in sheets:
            # We use .replace("_", " ").capitalize() to make it look clean
            self.tabs.addTab(s.replace("_", " ").capitalize())
        
        # Set the UI to match our current active sheet
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i).lower().replace(" ", "_") == self.current_sheet_name:
                self.tabs.setCurrentIndex(i)
                
        self.tabs.blockSignals(False)

    def switch_sheet(self, index):
        """Saves current data and loads the newly selected sheet."""
        if index == -1: return
        
        # SAFETY CHECK: Only save if we actually have data/schema defined
        if hasattr(self, 'schema') and self.schema:
            save_inventory(self.username, {"schema": self.schema, "data": self.data}, self.fernet, self.current_sheet_name)
        
        # Update name and load new data
        self.current_sheet_name = self.tabs.tabText(index).lower().replace(" ", "_")
        payload = load_inventory(self.username, self.fernet, self.current_sheet_name)
        
        self.schema = payload["schema"]
        self.data = payload["data"]
        self.refresh_table()

    def refresh_table(self):
        self.table.clear()
        self.table.setColumnCount(len(self.schema))
        self.table.setHorizontalHeaderLabels(
            [col.capitalize().replace("_", " ") for col in self.schema]
        )
        self.table.setRowCount(0)
        for item in self.data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col_index, key in enumerate(self.schema):
                value = str(item.get(key, ""))
                item_widget = QTableWidgetItem(value)
                item_widget.setFlags(item_widget.flags() & ~Qt.ItemIsEditable)
                # Force text color to follow COLOR_FG
                item_widget.setForeground(QColor(COLOR_FG))
                self.table.setItem(row, col_index, item_widget)

    def filter_inventory(self, text):
        text = text.lower()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)


    # CRUD Operations
    def add_item(self):
        dialog = self.item_dialog(self.schema)
        if dialog.exec() == QDialog.Accepted:
            new_item = dialog.get_data()
            new_item["last_checked"] = datetime.now().strftime("%Y-%m-%d")
            self.data.append(new_item)
            save_inventory(self.username, {"schema": self.schema, "data": self.data}, self.fernet, self.current_sheet_name)
            self.refresh_table()

    def edit_item(self):
        idx = self.get_selected_index()
        if idx is None: return
        item = self.data[idx]
        dialog = self.item_dialog(self.schema, item)
        if dialog.exec() == QDialog.Accepted:
            updated_item = dialog.get_data()
            updated_item["last_checked"] = datetime.now().strftime("%Y-%m-%d")
            self.data[idx] = updated_item
            save_inventory(self.username, {"schema": self.schema, "data": self.data}, self.fernet, self.current_sheet_name)
            self.refresh_table()


    # --- UPDATED RENAME LOGIC ---
    def rename_current_sheet(self):
        """Renames the current active sheet file using Ghost prompts with pre-save safety."""
        if self.current_sheet_name == "inventory":
            ghost_alert(self, "ACCESS DENIED", "The primary 'Inventory' sheet is protected and cannot be renamed.")
            return

        # 1. TACTICAL PRE-SAVE: Ensure the file physically exists before renaming
        save_inventory(self.username, {"schema": self.schema, "data": self.data}, self.fernet, self.current_sheet_name)

        old_name_display = self.current_sheet_name.replace("_", " ").capitalize()
        new_name, ok = ghost_prompt(self, "RENAME PROTOCOL", "ENTER NEW DESIGNATION:", placeholder=old_name_display)
        
        if ok and new_name.strip():
            new_sheet_id = new_name.strip().lower().replace(" ", "_")
            from inventory_manager import rename_inventory_file
            
            # 2. Attempt rename via manager
            success, error = rename_inventory_file(self.username, self.current_sheet_name, new_sheet_id)
            
            if success:
                self.current_sheet_name = new_sheet_id
                self.load_sheet_list() # Refresh tabs to show new name
            else:
                # This will now only trigger for genuine OS errors, not missing files
                ghost_alert(self, "SYSTEM ERROR", f"Rename failed: {error}")

    # --- UPDATED CREATE LOGIC ---
    def create_new_sheet(self):
        """Prompt user for a name and create a new inventory file via Ghost prompt."""
        name, ok = ghost_prompt(self, "NEW DATA SHEET", "ASSIGN SHEET NAME (e.g. Garage, Home):")
        if ok and name.strip():
            sheet_id = name.strip().lower().replace(" ", "_")
            new_payload = {
                "schema": ["name", "quantity", "location", "last_checked"], 
                "data": []
            }
            try:
                save_inventory(self.username, new_payload, self.fernet, sheet_id)
                self.load_sheet_list()
                for i in range(self.tabs.count()):
                    if self.tabs.tabText(i).lower().replace(" ", "_") == sheet_id:
                        self.tabs.setCurrentIndex(i)
                        break
            except Exception as e:
                ghost_alert(self, "FATAL ERROR", f"Could not initialize sheet: {e}")

    # --- UPDATED SELECTION LOGIC ---
    def get_selected_index(self):
        selected = self.table.currentRow()
        if selected == -1:
            ghost_alert(self, "SYSTEM NOTICE", "Target acquisition failed. Select a row first.")
            return None
        return selected

    # --- UPDATED DELETE LOGIC ---
    def delete_item(self):
        idx = self.get_selected_index()
        if idx is None: return
        # ghost_alert automatically turns red/TERMINATE if "DELETE" is in title
        confirm = ghost_alert(self, "CONFIRM DELETE", "Purge this item from local storage?")
        if confirm:
            del self.data[idx]
            save_inventory(self.username, {"schema": self.schema, "data": self.data}, self.fernet, self.current_sheet_name)
            self.refresh_table()

    # --- UPDATED EXPORT/IMPORT LOGIC ---
    def export_csv(self):
        try:
            current_sheet = self.tabs.tabText(self.tabs.currentIndex())
            save_path = export_inventory_to_csv(
                username=self.username, 
                payload={"schema": self.schema, "data": self.data},
                sheet_name=current_sheet 
            )
            ghost_alert(self, "EXPORT COMPLETE", f"Data uplinked to:\n{save_path}")
        except Exception as e:
            ghost_alert(self, "EXPORT FAILED", str(e))

    def import_csv(self):
        """Import CSV and automatically expand the schema to include new columns found in the file."""
        try:
            current_sheet = self.tabs.tabText(self.tabs.currentIndex())
            confirm = ghost_alert(self, "IMPORT OVERWRITE", 
                f"Proceed with importing into '{current_sheet}'?")
        
            if not confirm: return  

            user_dir = os.path.join(INVENTORY_DIR, self.username)
            path = os.path.join(user_dir, f"inv_{self.current_sheet_name.lower()}_export.csv")

            if not os.path.exists(path):
                ghost_alert(self, "FILE MISSING", f"Place CSV at: {path}")
                return

            import csv
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                new_data = list(reader)
                # SCHEMA RECOVERY: Get headers from the CSV file itself
                if new_data:
                    detected_schema = list(reader.fieldnames)
                else:
                    detected_schema = self.schema

            # Update the local state
            self.schema = detected_schema
            self.data = new_data
            
            # Save the updated schema AND data back to encrypted storage
            save_inventory(self.username, {"schema": self.schema, "data": self.data}, self.fernet, self.current_sheet_name)
            
            self.refresh_table()
            ghost_alert(self, "IMPORT SUCCESS", f"Synchronized {len(new_data)} items and {len(self.schema)} columns.")
            
        except Exception as e:
            ghost_alert(self, "SYSTEM CRITICAL", str(e))

    # --- UPDATED COLUMNS LOGIC ---
    def edit_columns(self):
        """Allows editing column names and ensures existing names are displayed in the prompt."""
        current_cols_text = "\n".join(self.schema)
        
        # We create the dialog manually to ensure the text is SET before exec
        dialog = TacticalDialog(
            self, 
            title="COLUMN CONFIG", 
            label="EDIT DESIGNATIONS (ONE PER LINE):", 
            is_multiline=True
        )
        # FORCE the current columns into the text box
        dialog.input_field.setPlainText(current_cols_text)
        
        if dialog.exec() == QDialog.Accepted:
            cols = dialog.input_field.toPlainText()
            new_schema = [c.strip().lower().replace(" ", "_") for c in cols.split("\n") if c.strip()]
            
            if not new_schema: return

            # Data Mapping: Keep data for columns that stayed the same
            new_data = []
            for row in self.data:
                # If count matches, map by index; otherwise, map by key name
                if len(new_schema) == len(self.schema):
                    updated_row = {new_schema[i]: row.get(self.schema[i], "") for i in range(len(new_schema))}
                else:
                    updated_row = {k: row.get(k, "") for k in new_schema}
                new_data.append(updated_row)
            
            self.data = new_data
            self.schema = new_schema
            save_inventory(self.username, {"schema": self.schema, "data": self.data}, self.fernet, self.current_sheet_name)
            self.refresh_table()


    # --- RE-ENGINEERED THEMED DIALOG ---
    class item_dialog(TacticalDialog):
        def __init__(self, schema, item=None):
            # 1. Initialize TacticalDialog with Ghost styling
            super().__init__(title="ITEM DETAILS", label="EDIT ATTRIBUTES:")
            self.schema = schema
            self.inputs = {}
            
            # 2. Setup the Form
            content_layout = QFormLayout()
            for field in schema:
                if field == "last_checked": continue
                val = item.get(field, "") if item else ""
                line_edit = QLineEdit(str(val))
                
                line_edit.setStyleSheet(f"""
                    background-color: rgba(0,0,0,0.3); 
                    color: {COLOR_ACCENT}; 
                    border: 1px solid {COLOR_BORDER};
                    padding: 8px;
                    font-family: 'Consolas';
                """)
                self.inputs[field] = line_edit
                
                label_widget = QLabel(f"{field.upper().replace('_', ' ')}:")
                label_widget.setStyleSheet(f"color: {COLOR_FG}; font-size: 10px; font-weight: bold;")
                content_layout.addRow(label_widget, line_edit)

            # 3. Inject Form & Cleanup UI
            self.input_field.hide() 
            self.container.layout().insertLayout(3, content_layout)
            
            # 4. Final Polish & Logic Connection
            self.confirm_btn.setText("SAVE CHANGES")
            self.confirm_btn.clicked.connect(self.accept)
            self.cancel_btn.clicked.connect(self.reject)

        def get_data(self):
            return {field: widget.text() for field, widget in self.inputs.items()}