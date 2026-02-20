from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QLabel, QPushButton, QInputDialog, QMessageBox,
    QListWidgetItem, QHBoxLayout, QProgressBar, QLineEdit, QFrame,
    QDialog, QDialogButtonBox, QFormLayout
)
from PySide6.QtCore import Qt, QSize
from project_manager import list_project_files, load_project_file, save_project_file, delete_project_file
from core.paths import PROJECTS_DIR, EVERYTHING_ELSE
import os
from .style_config import (
    T, FONT_MAIN, FONT_SIZE, STYLE_BUTTON, STYLE_INPUT
)

class ProjectsPage(QWidget):
    def __init__(self, username, passphrase, fernet):
        super().__init__()
        self.setObjectName("ProjectsPage")
        self.username = username
        self.passphrase = passphrase
        self.fernet = fernet

        # --- Main Layout ---
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(15)

        # Header Section
        header_container = QVBoxLayout()
        self.title_label = QLabel("MISSION CONTROL")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(f"""
            color: {T['ACCENT_SOLID']}; 
            font-family: '{FONT_MAIN}'; 
            font-size: 22px; 
            font-weight: 800; 
            letter-spacing: 1.5px; 
            margin-bottom: 5px;
        """)
        header_container.addWidget(self.title_label)

        # The Thick Divider Line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {T['ACCENT_SOLID']}; min-height: 2px; max-height: 2px;")
        header_container.addWidget(line)
        self.main_layout.addLayout(header_container)

        # --- Two-Pane Body ---
        self.body_layout = QHBoxLayout()
        
        # LEFT: Project Selection
        left_panel = QVBoxLayout()
        left_label = QLabel("ACTIVE PLANS")
        left_label.setStyleSheet(f"color: {T['ACCENT_SOLID']}; font-family: '{FONT_MAIN}'; font-weight: bold; font-size: 10px; letter-spacing: 1px;")
        left_panel.addWidget(left_label)
        
        self.project_list = QListWidget()
        self.project_list.setFixedWidth(220)
        self.project_list.setStyleSheet(self.get_list_style())
        self.project_list.itemClicked.connect(self.display_project)
        left_panel.addWidget(self.project_list)
        
        self.add_project_btn = QPushButton("+ New Project")
        self.add_project_btn.setStyleSheet(STYLE_BUTTON)
        self.add_project_btn.clicked.connect(self.add_project)
        left_panel.addWidget(self.add_project_btn)
        
        self.body_layout.addLayout(left_panel)

        # RIGHT: Task Workspace
        right_panel = QVBoxLayout()
        
        # --- Progress Bar ---
        progress_container = QVBoxLayout()
        self.progress_label = QLabel("INITIALIZING SYSTEM...") 
        self.progress_label.setStyleSheet(f"font-family: '{FONT_MAIN}'; font-size: 10px; color: {T['TEXT_MAIN']};")
        
        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ border: none; background-color: {T['BORDER']}; border-radius: 3px; }}
            QProgressBar::chunk {{ background-color: {T['ACCENT_SOLID']}; border-radius: 3px; }}
        """)
        
        progress_container.addWidget(self.progress_label)
        progress_container.addWidget(self.progress)
        right_panel.addLayout(progress_container)

        self.project_detail_list = QListWidget()
        self.project_detail_list.setStyleSheet(self.get_list_style())
        self.project_detail_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.project_detail_list.setWordWrap(True)
        right_panel.addWidget(self.project_detail_list)

        # Workspace Controls
        self.quick_add_input = QLineEdit()
        self.quick_add_input.setPlaceholderText("Quick add task to current project...")
        self.quick_add_input.setStyleSheet(STYLE_INPUT)
        self.quick_add_input.returnPressed.connect(self.handle_quick_add)
        right_panel.addWidget(self.quick_add_input)


        # --- UPDATED COMPACT BUTTONS ---
        task_btn_layout = QHBoxLayout()
        buttons = [
            ("Done ✅", self.mark_task_complete),
            ("Add Task", self.add_task),
            ("Edit Task", self.edit_task),
            ("Kill Task", self.delete_task),      # Shortened "Kill Task"
            ("Edit Proj.", self.edit_project_details),
            ("Delete", self.delete_project)   # Shortened "Delete"
        ]
        
        for text, func in buttons:
            btn = QPushButton(text)
            
            # Use 'in' to check for keywords so colors don't break if you change emojis
            if "Delete" in text or "Purge" in text:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #d9534f; 
                        color: white; 
                        border-radius: 8px; 
                        padding: 8px;
                        font-family: '{FONT_MAIN}'; 
                        font-weight: 900;
                        font-size: 11px;
                    }}
                    QPushButton:hover {{ background-color: #c9302c; }}
                """) 
            else:
                # Apply standard style but slightly smaller font for the compact fit
                btn.setStyleSheet(STYLE_BUTTON + f"; font-size: 11px; font-weight: 800; padding: 8px;")
            
            btn.clicked.connect(func)
            task_btn_layout.addWidget(btn)
        
        right_panel.addLayout(task_btn_layout)
        self.body_layout.addLayout(right_panel)
        
        self.main_layout.addLayout(self.body_layout)
        self.load_projects()

    def parse_suggestions(self, text):
        goals = []
        current_goal = None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("- Goal:"):
                if current_goal:
                    goals.append(current_goal)
                current_goal = {"goal": line[len("- Goal:"):].strip(), "tasks": []}
            elif line.startswith("- Task:") and current_goal:
                current_goal["tasks"].append(line[len("- Task:"):].strip())
        if current_goal:
            goals.append(current_goal)
        return goals


    def show_parsed_suggestions(self, ai_text):
        from PySide6.QtWidgets import QCheckBox

        parsed_goals = self.parse_suggestions(ai_text)
        self.suggestion_dialog = QDialog(self)
        self.suggestion_checkboxes = []
        layout = QVBoxLayout()

        for goal in parsed_goals:
            goal_label = QLabel(f"➜ Goal: {goal['goal']}")
            layout.addWidget(goal_label)

            for task in goal["tasks"]:
                checkbox = QCheckBox(f"• {task}")
                self.suggestion_checkboxes.append((checkbox, goal["goal"], task))
                layout.addWidget(checkbox)

        # Add the import button
        import_button = QPushButton("✅ Import Checked Tasks")
        import_button.clicked.connect(self.import_checked_suggestions)
        layout.addWidget(import_button)

        self.suggestion_dialog.setLayout(layout)
        self.suggestion_dialog.setWindowTitle("AI Suggestions")
        self.suggestion_dialog.exec()


    def import_checked_suggestions(self):
        if not hasattr(self, "current_project_data") or not hasattr(self, "suggestion_checkboxes"):
            return

        for checkbox, goal, task in self.suggestion_checkboxes:
            if checkbox.isChecked():
                if goal not in self.current_project_data["goals"]:
                    self.current_project_data["goals"].append(goal)
                self.current_project_data["tasks"].append({
                    "goal": goal,
                    "task": task,
                    "status": "incomplete"
                })

        save_project_file(self.username, self.current_project_data, self.fernet)

        # Refresh display
        current_item = self.project_list.currentItem()
        if current_item:
            self.display_project(current_item)

        # Close dialog
        self.suggestion_dialog.accept()


    def edit_project_details(self):
        """Aligned and dynamic dialog for editing project info."""
        if not hasattr(self, "current_project_data"):
            return

        data = self.current_project_data
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Project Command Center")
        dialog.setMinimumWidth(500)
        main_layout = QVBoxLayout(dialog)

        # ─── SECTION 1: ALIGNED CORE INFO ──────────────────────────
        # QFormLayout ensures labels and inputs align perfectly
        form_layout = QFormLayout()
        name_input = QLineEdit(data["project"])
        desc_input = QLineEdit(data["description"])
        date_input = QLineEdit(data["deadline"])
        
        form_layout.addRow("Project Name:", name_input)
        form_layout.addRow("Description:", desc_input)
        form_layout.addRow("Deadline:", date_input)
        main_layout.addLayout(form_layout)

        # ─── SECTION 2: DYNAMIC GOALS ──────────────────────────────
        main_layout.addWidget(QLabel("\nPROJECT GOALS:"))
        goals_container = QVBoxLayout()
        goal_inputs = []

        def add_goal_row(initial_val=""):
            row_layout = QHBoxLayout()
            new_input = QLineEdit(initial_val)
            goal_inputs.append(new_input)
            row_layout.addWidget(new_input)
            
            del_btn = QPushButton("✕")
            del_btn.setFixedWidth(30)
            del_btn.setStyleSheet("color: red; border: none; font-weight: bold;")
            del_btn.clicked.connect(lambda: remove_goal_row(row_layout, new_input))
            row_layout.addWidget(del_btn)
            goals_container.addLayout(row_layout)

        def remove_goal_row(layout_to_kill, input_to_kill):
            if input_to_kill in goal_inputs:
                goal_inputs.remove(input_to_kill)
            while layout_to_kill.count():
                child = layout_to_kill.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            goals_container.removeItem(layout_to_kill)

        for g in data.get("goals", []):
            add_goal_row(g)

        main_layout.addLayout(goals_container)

        add_more_btn = QPushButton("+ Add Another Goal")
        add_more_btn.setStyleSheet(STYLE_BUTTON)
        add_more_btn.clicked.connect(lambda: add_goal_row())
        main_layout.addWidget(add_more_btn)

        # ─── SECTION 3: ACTIONS ────────────────────────────────────
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        main_layout.addWidget(btns)

        if dialog.exec() == QDialog.Accepted:
            updated_goals = [i.text().strip() for i in goal_inputs if i.text().strip()]
            data["project"] = name_input.text().strip()
            data["description"] = desc_input.text().strip()
            data["deadline"] = date_input.text().strip()
            data["goals"] = updated_goals

            if save_project_file(self.username, data, self.fernet):
                # 1. Refresh the sidebar list
                self.load_projects()
                
                # 2. Find the new name in the list (formatted as filename)
                target_name = data["project"].replace(" ", "_").lower()
                
                # 3. Re-select the item so display_project has a valid target
                for i in range(self.project_list.count()):
                    if self.project_list.item(i).text().lower() == target_name:
                        self.project_list.setCurrentRow(i)
                        self.display_project(self.project_list.item(i))
                        break


    def get_list_style(self):
        return f"""
            QListWidget {{
                background-color: {T['BG_CARD']};
                border: 1px solid {T['BORDER']};
                border-radius: 12px;
                outline: none;
                padding: 10px;
            }}
            QListWidget::item {{
                background: transparent;
                border: none;
                margin-bottom: 4px;
                border-radius: 8px;
            }}
            QListWidget::item:hover {{
                background-color: {T['BG_HOVER']};
            }}
            QListWidget::item:selected {{
                background-color: {T['ACCENT_GLOW']};
                border-left: 4px solid {T['ACCENT_SOLID']};
                color: white;
            }}
        """


    def add_task_to_project(self, goal_title, task):
        if not hasattr(self, "current_project_data"):
            return
        for goal in self.current_project_data["goals"]:
            if goal == goal_title:
                break
        else:
            self.current_project_data["goals"].append(goal_title)
        self.current_project_data["tasks"].append({"goal": goal_title, "task": task, "status": "incomplete"})
        save_project_file(self.username, self.current_project_data, self.fernet)
        current_item = self.project_list.currentItem()
        if current_item:
            self.display_project(current_item)

    def load_projects(self):
        from project_manager import get_user_project_dir
        user_dir = get_user_project_dir(self.username)
        
        if not os.path.exists(user_dir):
            self.project_list.clear()
            return

        self.project_files = [
            f for f in os.listdir(user_dir)
            if f.endswith(".enc") and not f.startswith(".")
        ]
        self.project_list.clear()
        for f in self.project_files:
            self.project_list.addItem(f[:-4])

    def get_active_fernet(self, filename):
        """Returns the specific Fernet key for a project, or the master key if local."""
        from cryptography.fernet import Fernet
        import base64
        import json

        key_store_path = os.path.join(EVERYTHING_ELSE, "inventory", "project_keys.json")
        
        if os.path.exists(key_store_path):
            try:
                with open(key_store_path, "r") as f:
                    keys = json.load(f)
                
                if filename in keys:
                    # Found a peer key! Decode it and return a new Fernet instance
                    raw_key = base64.b64decode(keys[filename])
                    return Fernet(raw_key)
            except Exception as e:
                print(f"[Keychain] Warning: Could not parse project_keys.json: {e}")

        # Fallback: Use your own master key
        return self.fernet

    def handle_quick_add(self):
        """Processes the rapid-entry task bar, assigning tasks to the selected goal."""
        task_text = self.quick_add_input.text().strip()
        if not task_text or not hasattr(self, "current_project_data"):
            return

        # --- CONTEXTUAL LOGIC ---
        # Find the currently selected item in the project detail list
        selected_item = self.project_detail_list.currentItem()
        target_goal = None

        if selected_item:
            current_text = selected_item.text()
            # If a goal header is selected (starts with 🎯)
            if "🎯" in current_text:
                target_goal = current_text.replace("🎯", "").strip().title()
            # If a task is selected (starts with ⤷), find its parent goal
            elif "⤷" in current_text:
                # Iterate backwards from current row to find the nearest Goal header
                curr_row = self.project_detail_list.currentRow()
                for i in range(curr_row, -1, -1):
                    header_text = self.project_detail_list.item(i).text()
                    if "🎯" in header_text:
                        target_goal = header_text.replace("🎯", "").strip().title()
                        break
        
        # If no goal is selected, we can either default to the first goal 
        # or warn the user. Let's default to the first goal if available.
        if not target_goal and self.current_project_data.get("goals"):
            target_goal = self.current_project_data["goals"][0]
        elif not target_goal:
            QMessageBox.warning(self, "No Goal", "Please create or select a Goal first.")
            return

        # Create task assigned to the detected goal
        # Note: We match case-insensitively or via strip to ensure it hits the right bucket
        actual_goal_name = next((g for g in self.current_project_data["goals"] if g.lower() == target_goal.lower()), target_goal)

        new_task = {"goal": actual_goal_name, "task": task_text, "status": "incomplete"}
        self.current_project_data["tasks"].append(new_task)
    
        if save_project_file(self.username, self.current_project_data, self.fernet):
            self.quick_add_input.clear()
            self.display_project(self.project_list.currentItem())
            # Maintain focus for rapid entry
            self.quick_add_input.setFocus()

    def display_project(self, item):
        if item is None: return
        search_text = item.text().lower()
        self.current_project_file = next((f for f in self.project_files if f[:-4].lower() == search_text), None)
        if not self.current_project_file: return

        active_key = self.get_active_fernet(self.current_project_file)
        data = load_project_file(self.username, self.current_project_file, active_key)
        if not data: return

        self.current_project_data = data
        self.project_detail_list.clear()

        # Update Progress
        all_tasks = data.get("tasks", [])
        total = len(all_tasks)
        completed = len([t for t in all_tasks if t.get("status") == "complete"])
        calc_percentage = int((completed / total) * 100) if total > 0 else 0
        self.progress.setValue(calc_percentage)
        self.progress_label.setText(f"COMPLETION: {calc_percentage}%")

        def add_styled_item(html_text, raw_text=None, is_header=False, indent=False):
            list_item = QListWidgetItem()
            if raw_text:
                list_item.setData(Qt.UserRole, raw_text)
            
            container = QWidget()
            # Background transparent so the QListWidget selection highlight shows through
            container.setStyleSheet("background: transparent; border: none;")
            layout = QVBoxLayout(container)
            
            label = QLabel(html_text)
            label.setWordWrap(True)
            
            # Set width slightly narrower than the list to prevent horizontal scroll popping
            label.setFixedWidth(self.project_detail_list.width() - 80)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            
            style = f"color: {T['TEXT_MAIN']}; font-size: {'13px' if is_header else '12px'}; font-family: '{FONT_MAIN}';"
            if is_header: style += "font-weight: bold;"
            label.setStyleSheet(style)
            
            # Increased vertical padding (15px) for much better breathing room
            left_m = 55 if indent else 25
            layout.setContentsMargins(left_m, 15, 25, 15) 
            layout.setSpacing(0)
            layout.addWidget(label)
            
            self.project_detail_list.addItem(list_item)
            self.project_detail_list.setItemWidget(list_item, container)
            
            # Recalculate size with a 10px height buffer to prevent cutoffs
            container.adjustSize()
            list_item.setSizeHint(container.sizeHint() + QSize(0, 10))

        # 1. Metadata
        add_styled_item(f"<b style='color:{T['ACCENT_SOLID']}'>FILE:</b> {self.current_project_file}")
        add_styled_item(f"<b style='color:{T['ACCENT_SOLID']}'>DESC:</b> {data.get('description', '...')}")
        deadline = data.get('deadline', 'NOT SET')
        add_styled_item(f"<b style='color:{T['ACCENT_SOLID']}'>DEADLINE:</b> <span style='color: #FF5555;'>{deadline}</span>")
        
        # 2. Tasks logic
        assigned_tasks = []
        for goal in data.get("goals", []):
            # Goal Header
            add_styled_item(f"<span style='color: #FFCC00;'>🎯 {goal.upper()}</span>", is_header=True)
            for t in all_tasks:
                if t.get("goal") == goal:
                    status_icon = "✅" if t["status"] == "complete" else "⬜"
                    html = f"<span style='color:#666;'>⤷</span> {status_icon} {t['task']}"
                    add_styled_item(html, raw_text=t['task'], indent=True)
                    assigned_tasks.append(t)

        # 3. Uncategorized
        uncategorized = [t for t in all_tasks if t not in assigned_tasks]
        if uncategorized:
            add_styled_item("<span style='color: #AA88FF;'>📦 UNCATEGORIZED</span>", is_header=True)
            for t in uncategorized:
                status_icon = "✅" if t["status"] == "complete" else "⬜"
                html = f"<span style='color:#666;'>⤷</span> {status_icon} {t['task']}"
                add_styled_item(html, raw_text=t['task'], indent=True)


    def add_project(self):
        """Dynamic dialog for creating a brand new project with infinite goals."""
        data = {"project": "", "description": "", "deadline": "", "goals": [], "tasks": []} 
        dialog = QDialog(self)
        dialog.setWindowTitle("Initialize New Project")
        dialog.setMinimumWidth(500)
        main_layout = QVBoxLayout(dialog)

        # Aligned Header
        form_layout = QFormLayout()
        name_input = QLineEdit()
        desc_input = QLineEdit()
        date_input = QLineEdit()
        form_layout.addRow("Project Name:", name_input)
        form_layout.addRow("Description:", desc_input)
        form_layout.addRow("Deadline:", date_input)
        main_layout.addLayout(form_layout)

        # Goals Section
        main_layout.addWidget(QLabel("\nPROJECT GOALS:"))
        goals_container = QVBoxLayout()
        goal_inputs = []

        def add_goal_row():
            row_layout = QHBoxLayout()
            new_input = QLineEdit()
            goal_inputs.append(new_input)
            row_layout.addWidget(new_input)
            
            del_btn = QPushButton("✕")
            del_btn.setFixedWidth(30)
            del_btn.setStyleSheet("color: red; border: none;")
            del_btn.clicked.connect(lambda: remove_goal_row(row_layout, new_input))
            row_layout.addWidget(del_btn)
            goals_container.addLayout(row_layout)

        def remove_goal_row(layout_to_kill, input_to_kill):
            goal_inputs.remove(input_to_kill)
            while layout_to_kill.count():
                child = layout_to_kill.takeAt(0)
                if child.widget(): child.widget().deleteLater()
            goals_container.removeItem(layout_to_kill)

        # Start with one empty goal box
        add_goal_row()
        main_layout.addLayout(goals_container)

        add_more_btn = QPushButton("+ Add Another Goal")
        add_more_btn.setStyleSheet(STYLE_BUTTON)
        add_more_btn.clicked.connect(add_goal_row)
        main_layout.addWidget(add_more_btn)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        main_layout.addWidget(btns)

        if dialog.exec() == QDialog.Accepted:
            updated_goals = [i.text().strip() for i in goal_inputs if i.text().strip()]
            data["project"] = name_input.text().strip()
            data["description"] = desc_input.text().strip()
            data["deadline"] = date_input.text().strip()
            data["goals"] = updated_goals

            if save_project_file(self.username, data, self.fernet):
                self.load_projects()
                
                # --- BETTER RE-SELECTION LOGIC ---
                # Look for the project name we just saved (formatted as a filename)
                target_name = data["project"].replace(" ", "_").lower()
                for i in range(self.project_list.count()):
                    if self.project_list.item(i).text().lower() == target_name:
                        self.project_list.setCurrentRow(i)
                        self.display_project(self.project_list.item(i))
                        break


    def delete_project(self):
        if not hasattr(self, "current_project_file"):
            QMessageBox.warning(self, "No Selection", "Select a project to delete.")
            return
            
        confirm = QMessageBox.question(self, "Confirm", f"Delete {self.current_project_file}?", QMessageBox.Yes | QMessageBox.No)
        
        if confirm == QMessageBox.Yes:
            from project_manager import get_user_project_dir
            user_dir = get_user_project_dir(self.username)
            full_filepath = os.path.join(user_dir, self.current_project_file)
            
            # Call the manager to delete the real file
            if delete_project_file(full_filepath):
                self.load_projects()
                self.project_detail_list.clear() # Clear the old text
                self.progress.setValue(0)
                # Success feedback in terminal for debugging
                print(f"[GhostDrive] Successfully deleted: {full_filepath}")
            else:
                QMessageBox.critical(self, "Error", "Could not delete the file from disk.")


    def mark_task_complete(self):
        if not hasattr(self, "current_project_data"): return
        selected_item = self.project_detail_list.currentItem()
    
        # 🔥 FIX: Get the raw name from UserRole, not .text()
        task_name = selected_item.data(Qt.UserRole) if selected_item else None
        if not task_name: return
    
        current_row = self.project_detail_list.currentRow()

        for t in self.current_project_data["tasks"]:
            if t["task"] == task_name:
                t["status"] = "incomplete" if t["status"] == "complete" else "complete"
                break

        active_key = self.get_active_fernet(self.current_project_file)
        if save_project_file(self.username, self.current_project_data, active_key):
            self.display_project(self.project_list.currentItem())
            self.project_detail_list.setCurrentRow(current_row)

    def edit_task(self):
        if not hasattr(self, "current_project_data"): return
        selected_item = self.project_detail_list.currentItem()
        
        # Pull the raw data we stored earlier
        task_name = selected_item.data(Qt.UserRole) if selected_item else None
        
        if not task_name:
            QMessageBox.warning(self, "No Selection", "Select a task to edit.")
            return

        task = next((t for t in self.current_project_data["tasks"] if t["task"] == task_name), None)
        if not task: return

        new_text, ok1 = QInputDialog.getText(self, "Edit Text", "Modify task text:", text=task["task"])
        if not ok1: return
        new_status, ok2 = QInputDialog.getItem(self, "Edit Status", "Choose status:", ["incomplete", "complete"], editable=False)
        if not ok2: return

        task["task"] = new_text
        task["status"] = new_status
        save_project_file(self.username, self.current_project_data, self.get_active_fernet(self.current_project_file))
        self.display_project(self.project_list.currentItem())

    def delete_task(self):
        if not hasattr(self, "current_project_data"): return
        selected_item = self.project_detail_list.currentItem()
        task_name = selected_item.data(Qt.UserRole) if selected_item else None
        
        if not task_name:
            QMessageBox.warning(self, "No Selection", "Select a task to delete.")
            return

        confirm = QMessageBox.question(self, "Confirm Deletion", f"Delete task:\n'{task_name}'?", QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes: return

        self.current_project_data["tasks"] = [t for t in self.current_project_data["tasks"] if t["task"] != task_name]
        save_project_file(self.username, self.current_project_data, self.get_active_fernet(self.current_project_file))
        self.display_project(self.project_list.currentItem())


    def add_task(self):
        if not hasattr(self, "current_project_data"): return
        goal, ok1 = QInputDialog.getItem(self, "Assign to Goal", "Select goal (or Chaos Queue):", self.current_project_data["goals"] + ["Chaos Queue"], editable=False)
        if not ok1: return
        task_text, ok2 = QInputDialog.getText(self, "Task", "Enter task:")
        if not ok2: return

        new_task = {
            "goal": None if goal == "Chaos Queue" else goal,
            "task": task_text,
            "status": "incomplete"
        }
        self.current_project_data["tasks"].append(new_task)
        save_project_file(self.username, self.current_project_data, self.fernet)
        current_item = self.project_list.currentItem()
        if current_item:
            self.display_project(current_item)


    def generate_ai_suggestions(self):
        if not hasattr(self, "current_project_data"):
            QMessageBox.warning(self, "No Project", "Open a project first.")
            return

        data = self.current_project_data
        title = data["project"]
        description = data["description"]
        deadline = data["deadline"]
        goals = data["goals"]
        tasks = data["tasks"]

        goal_map = {}
        for g in goals:
            goal_map[g] = [t["task"] for t in tasks if t.get("goal") == g]
        chaos = [t["task"] for t in tasks if t.get("goal") not in goals]

        goals_and_tasks = "\n".join(
            f"- {g}:\n" + "\n".join(f"  • {t}" for t in goal_map[g])
            for g in goal_map
        )
        if chaos:
            goals_and_tasks += "\n- Chaos Queue:\n" + "\n".join(f"  • {t}" for t in chaos)

        prompt = f"""
You are an expert project planner AI.

Here is a project:
Title: {title}
Description: {description}
Deadline: {deadline}

Goals and Tasks:
{goals_and_tasks}

Your job:
1. Suggest 1–2 new goals to improve the project or catch blind spots.
2. Suggest 1–2 new tasks for goals that seem vague or incomplete.

✳️ OUTPUT FORMAT (strictly follow this, no narration):

**New Goals:**
- Goal: <goal name>
  - Task: <task 1>
  - Task: <task 2>

**Suggested Tasks:**
- Goal: <existing goal name>
  - Task: <task 1>
  - Task: <task 2>

DO NOT WRITE ANYTHING ELSE — only use the format above.
""".strip()



        try:
            from Everything_else.model_registry import load_model_from_config, get_stop_sequence
            llm_fn, cfg = load_model_from_config("jynx_expert_math")

            buffer = ""
            for chunk in llm_fn(
                prompt,
                stream_override=True,
                max_tokens=cfg.get("generation_token_limit", 300),
                temperature=0.7,
                stop=get_stop_sequence("jynx_expert_math"),
            ):
                token = chunk.get("choices", [{}])[0].get("text") or \
                        chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                buffer += token or ""

            QMessageBox.information(self, "AI Suggestions", buffer.strip())

        except Exception as e:
            QMessageBox.critical(self, "AI Error", f"Something went wrong:\n\n{str(e)}")

