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
    STYLE_LABEL, STYLE_BUTTON, COLOR_PAGE_BG, COLOR_BORDER
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
        self.search_bar.setPlaceholderText("Search inventory...")
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
                color: white;
                border: 1px solid {COLOR_BG};
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


    def rename_current_sheet(self):
        """Renames the current active sheet file and updates the UI."""
        if self.current_sheet_name == "inventory":
            QMessageBox.information(self, "Protected", "The primary 'Inventory' sheet cannot be renamed.")
            return

        old_name = self.current_sheet_name.replace("_", " ").capitalize()
        new_name, ok = QInputDialog.getText(self, "Rename Sheet", "New name:", text=old_name)
        
        if ok and new_name.strip():
            new_sheet_id = new_name.strip().lower().replace(" ", "_")
            
            # Use the manager to rename the file on disk
            from inventory_manager import rename_inventory_file
            success, error = rename_inventory_file(self.username, self.current_sheet_name, new_sheet_id)
            
            if success:
                self.current_sheet_name = new_sheet_id
                self.load_sheet_list()
            else:
                QMessageBox.critical(self, "Rename Failed", f"Could not rename: {error}")

    def create_new_sheet(self):
        """Prompt user for a name and create a new inventory file."""
        name, ok = QInputDialog.getText(self, "New Sheet", "Sheet Name (e.g. Garage, Home):")
        if ok and name.strip():
            # Clean the name for the filename
            sheet_id = name.strip().lower().replace(" ", "_")
            
            # 1. Prepare default data for the new sheet
            new_payload = {
                "schema": ["name", "quantity", "location", "last_checked"], 
                "data": []
            }
            
            # 2. Save it to disk immediately so it exists for load_sheet_list to find
            try:
                save_inventory(self.username, new_payload, self.fernet, sheet_id)
                
                # 3. Refresh the tab list to show the new sheet
                self.load_sheet_list()
                
                # 4. Switch to the new tab
                for i in range(self.tabs.count()):
                    if self.tabs.tabText(i).lower().replace(" ", "_") == sheet_id:
                        self.tabs.setCurrentIndex(i)
                        break
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create sheet: {e}")


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

    def get_selected_index(self):
        selected = self.table.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Invalid", "Select an item first.")
            return None
        return selected

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

    def delete_item(self):
        idx = self.get_selected_index()
        if idx is None: return
        confirm = QMessageBox.question(self, "Confirm Delete", f"Delete item?")
        if confirm == QMessageBox.Yes:
            del self.data[idx]
            save_inventory(self.username, {"schema": self.schema, "data": self.data}, self.fernet)
            self.refresh_table()

    def export_csv(self):
        try:
            # 1. Grab the name of the active tab (e.g., "Garage")
            current_sheet = self.tabs.tabText(self.tabs.currentIndex())
        
            # 2. Use the manager to handle the naming and saving
            save_path = export_inventory_to_csv(
                username=self.username, 
                payload={"schema": self.schema, "data": self.data},
                sheet_name=current_sheet  # <--- CRITICAL
            )
            QMessageBox.information(self, "Export Successful", f"Exported {current_sheet} to:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))

    def import_csv(self):
        try:
            current_sheet = self.tabs.tabText(self.tabs.currentIndex())
        
            confirm = QMessageBox.question(self, "Confirm Overwrite", 
                f"Importing will overwrite your '{current_sheet}' data. Continue?", 
                QMessageBox.Yes | QMessageBox.No)
        
            if confirm != QMessageBox.Yes: return  

            # Create the dictionary to pass
            temp_payload = {"schema": self.schema, "data": self.data}
        
            # FIX: Change 'payload_ref' to 'current_payload' to match the manager function
            success, result = import_inventory_from_csv(
                username=self.username,
                fernet=self.fernet,
                current_payload=temp_payload, # <--- FIXED NAME HERE
                sheet_name=current_sheet
            )

            if success:
                # Sync the UI variables back
                self.schema = temp_payload["schema"]
                self.data = temp_payload["data"]
                self.refresh_table()
                QMessageBox.information(self, "Import Successful", f"'{current_sheet}' updated ({result} items).")
            else:
                QMessageBox.warning(self, "Import Failed", result) # result is the error message if success is False

        except Exception as e:
            QMessageBox.critical(self, "Import Failed", str(e))

    def edit_columns(self):
        cols, ok = QInputDialog.getMultiLineText(self, "Edit Columns", "Column names (one per line):", "\n".join(self.schema)) 
        if ok:
            new_schema = [c.strip().lower().replace(" ", "_") for c in cols.split("\n") if c.strip()]
            if not new_schema: return
            self.schema = new_schema
            save_inventory(self.username, {"schema": self.schema, "data": self.data}, self.fernet)
            self.refresh_table()

    # --- THEMED INNER DIALOG ---
    class item_dialog(QDialog):
        def __init__(self, schema, item=None):
            super().__init__()
            self.setWindowTitle("Item Details")
            self.schema = schema
            self.inputs = {}
            layout = QFormLayout(self)
            
            # Apply Master Theme to Dialog
            self.setStyleSheet(f"background-color: {COLOR_BG}; color: {COLOR_FG}; font-family: '{FONT_FAMILY}';")

            for field in schema:
                if field == "last_checked": continue
                val = item.get(field, "") if item else ""
                line_edit = QLineEdit(str(val))
                
                # Input styling
                line_edit.setStyleSheet(f"""
                    background-color: {COLOR_BUTTON}; 
                    color: {COLOR_FG}; 
                    border: 1px solid {COLOR_ACCENT};
                    padding: 4px;
                """)
                self.inputs[field] = line_edit
                
                label = QLabel(f"{field.capitalize().replace('_', ' ')}:")
                label.setStyleSheet(f"color: {COLOR_FG}; font-weight: bold;")
                layout.addRow(label, line_edit)

            btn = QPushButton("Save")
            btn.setStyleSheet(STYLE_BUTTON)
            btn.clicked.connect(self.accept)
            layout.addWidget(btn)

        def get_data(self):
            return {field: widget.text() for field, widget in self.inputs.items()}