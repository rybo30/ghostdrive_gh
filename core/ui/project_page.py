# [project_page.py]

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
    T, FONT_MAIN, FONT_SIZE, STYLE_BUTTON, STYLE_INPUT,
    ghost_prompt, ghost_alert, TacticalDialog
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
            ("Edit Task", self.edit_task),
            ("Kill Task", self.delete_task),
            ("Edit Proj.", self.edit_project_details),
            ("Delete", self.delete_project)
        ]
        
        for text, func in buttons:
            btn = QPushButton(text)
            
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
        """Aligned and dynamic dialog for editing project info using TacticalDialog."""
        if not hasattr(self, "current_project_data"):
            return

        data = self.current_project_data
        
        # 1. Initialize our custom TacticalDialog
        # We set label to "PROJECT PARAMETERS" to fit the theme
        dialog = TacticalDialog(self, title="PROJECT CONFIGURATION", label="MISSION PARAMETERS")
        
        # 2. Hide the default single input field since we are building a custom form
        dialog.input_field.hide()
        
        # 3. Build the custom form layout
        form_container = QWidget()
        form_layout = QFormLayout(form_container)
        form_layout.setSpacing(10)

        # Apply specific styling to labels within the form to match the gold theme
        label_style = f"color: {T['PROTOCOL_GOLD']}; font-family: 'Consolas'; font-size: 11px; font-weight: bold;"
        
        name_input = QLineEdit(data["project"])
        desc_input = QLineEdit(data["description"])
        date_input = QLineEdit(data["deadline"])
        
        # Apply the tactical input style
        for inp in [name_input, desc_input, date_input]:
            inp.setStyleSheet(STYLE_INPUT)

        # Create custom labels for the form to ensure they look "Tactical"
        lbl_name = QLabel("PROJECT NAME:"); lbl_name.setStyleSheet(label_style)
        lbl_desc = QLabel("DESCRIPTION:"); lbl_desc.setStyleSheet(label_style)
        lbl_date = QLabel("DEADLINE:"); lbl_date.setStyleSheet(label_style)

        form_layout.addRow(lbl_name, name_input)
        form_layout.addRow(lbl_desc, desc_input)
        form_layout.addRow(lbl_date, date_input)

        # 4. Handle Goals Section
        goals_header = QLabel("\nOPERATIONAL GOALS:")
        goals_header.setStyleSheet(f"color: {T['PROTOCOL_GOLD']}; font-weight: bold; font-size: 10px; letter-spacing: 1px;")
        
        goals_container = QVBoxLayout()
        goal_inputs = []

        def add_goal_row(initial_val=""):
            row_layout = QHBoxLayout()
            new_input = QLineEdit(initial_val)
            new_input.setStyleSheet(STYLE_INPUT)
            goal_inputs.append(new_input)
            row_layout.addWidget(new_input)
            
            del_btn = QPushButton("✕")
            del_btn.setFixedWidth(30)
            del_btn.setStyleSheet("color: #da3633; background: transparent; border: 1px solid #da3633; border-radius: 4px; font-weight: bold;")
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


        add_more_btn = QPushButton("+ ADD PROJECT GOAL")
        
        GOLD = T['PROTOCOL_GOLD']
        BG_ALPHA = "rgba(255, 176, 0, 0.15)" # Same alpha used in Confirm button
        LINE = T['HUD_LINE']

        add_more_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_ALPHA};
                color: {GOLD};
                border: 1px solid {LINE};
                border-radius: 4px;
                padding: 10px;
                font-family: 'Consolas';
                font-weight: bold;
                font-size: 11px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 176, 0, 0.25);
                border: 1px solid {GOLD};
            }}
            QPushButton:pressed {{
                background-color: {T['BG_HOVER']};
            }}
        """)
        add_more_btn.setCursor(Qt.PointingHandCursor)
        add_more_btn.clicked.connect(lambda: add_goal_row())

        # 5. Inject everything into the TacticalDialog's layout
        target_layout = dialog.container.layout()
        target_layout.insertWidget(3, form_container)
        target_layout.insertWidget(4, goals_header)
        target_layout.insertLayout(5, goals_container)
        target_layout.insertWidget(6, add_more_btn)
        
        # Add a small spacer after the button to separate it from the Confirm/Abort row
        target_layout.insertSpacing(7, 10)

        # 6. Execute and Save
        if dialog.exec() == QDialog.Accepted:
            updated_goals = [i.text().strip() for i in goal_inputs if i.text().strip()]
            data["project"] = name_input.text().strip()
            data["description"] = desc_input.text().strip()
            data["deadline"] = date_input.text().strip()
            data["goals"] = updated_goals

            if save_project_file(self.username, data, self.fernet):
                self.load_projects()
                target_name = data["project"].replace(" ", "_").lower()
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

        # 1. Grab current selection
        selected_item = self.project_detail_list.currentItem()
        target_goal = None

        # 2. Contextual Detection using UserRole data
        if selected_item:
            # We stored the Goal Name in UserRole + 1 during display_project
            target_goal = selected_item.data(Qt.UserRole + 1)
            curr_row = self.project_detail_list.currentRow()
        else:
            curr_row = 0

        # 3. Fallback to first goal if nothing is selected or data is missing
        goals_list = self.current_project_data.get("goals", [])
        
        if not target_goal and goals_list:
            target_goal = goals_list[0]
        elif not target_goal:
            ghost_alert(self, "SYSTEM ERROR", "NO OPERATIONAL GOAL DETECTED. SELECT A GOAL FIRST.")
            return

        # 4. Final Verification: Ensure target_goal exists in our data
        # (This handles any weird edge cases where selection might be stale)
        actual_goal_name = next(
            (g for g in goals_list if g.lower() == str(target_goal).lower()), 
            goals_list[0] if goals_list else "General Operations"
        )

        # 5. Create and Save
        new_task = {
            "goal": actual_goal_name, 
            "task": task_text, 
            "status": "incomplete"
        }
        
        if "tasks" not in self.current_project_data:
            self.current_project_data["tasks"] = []
            
        self.current_project_data["tasks"].append(new_task)

        if save_project_file(self.username, self.current_project_data, self.fernet):
            self.quick_add_input.clear()
            
            # Refresh the UI
            self.display_project(self.project_list.currentItem())
            
            # --- UI QUALITY OF LIFE ---
            # Restore selection to the same row so the user can rapid-fire tasks into the same goal
            if self.project_detail_list.count() > curr_row:
                self.project_detail_list.setCurrentRow(curr_row)
            
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

        def add_styled_item(html_text, raw_text=None, is_header=False, indent=False, goal_owner=None):
            list_item = QListWidgetItem()
    
            if raw_text:
                list_item.setData(Qt.UserRole, raw_text)
    
            if goal_owner:
                list_item.setData(Qt.UserRole + 1, goal_owner)
            elif is_header:
                clean_goal = html_text.replace("<span style='color: #FFCC00;'>🎯 ", "").replace("</span>", "").strip()
                list_item.setData(Qt.UserRole + 1, clean_goal)

            container = QWidget()
            container.setStyleSheet("background: transparent; border: none;")
            layout = QVBoxLayout(container)
            
            # --- MARGINS ---
            left_m = 55 if indent else 25
            right_m = 45  # Keep that nice wide right margin
            top_bottom_m = 12 
            layout.setContentsMargins(left_m, top_bottom_m, right_m, top_bottom_m) 
            layout.setSpacing(0)

            label = QLabel(html_text)
            label.setWordWrap(True)
            
            # --- DYNAMIC WIDTH & HEIGHT ---
            # 1. Calc width based on viewport
            available_width = self.project_detail_list.viewport().width() - left_m - right_m - 20
            label.setFixedWidth(available_width)
            
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            
            style = f"color: {T['TEXT_MAIN']}; font-size: {'13px' if is_header else '12px'}; font-family: '{FONT_MAIN}';"
            if is_header: style += "font-weight: bold;"
            label.setStyleSheet(style)
            
            layout.addWidget(label)
            
            # --- THE FIX: FORCE GEOMETRY UPDATE ---
            self.project_detail_list.addItem(list_item)
            self.project_detail_list.setItemWidget(list_item, container)
            
            # This forces the label to calculate how tall it needs to be 
            # now that the width is fixed and word-wrap is on.
            container.adjustSize() 
            
            # We add a small vertical buffer (10px) to the height hint 
            # to ensure the descenders (g, y, p) don't get clipped.
            final_size = container.sizeHint()
            list_item.setSizeHint(QSize(final_size.width(), final_size.height() + 10))

        # 1. Metadata Headers
        add_styled_item(f"<b style='color:{T['ACCENT_SOLID']}'>FILE:</b> {self.current_project_file}")
        add_styled_item(f"<b style='color:{T['ACCENT_SOLID']}'>DESC:</b> {data.get('description', '...')}")
        deadline = data.get('deadline', 'NOT SET')
        add_styled_item(f"<b style='color:{T['ACCENT_SOLID']}'>DEADLINE:</b> <span style='color: #FF5555;'>{deadline}</span>")
        
        # 2. Tasks logic (FIXED: Defined 'html' before passing it)
        assigned_tasks = []
        for goal in data.get("goals", []):
            add_styled_item(f"<span style='color: #FFCC00;'>🎯 {goal.upper()}</span>", is_header=True, goal_owner=goal)
    
            for t in all_tasks:
                if t.get("goal") == goal:
                    status_icon = "✅" if t.get("status") == "complete" else "⬜"
                    # Define the HTML string here!
                    task_html = f"<span style='color:#666;'>⤷</span> {status_icon} {t['task']}"
                    add_styled_item(task_html, raw_text=t['task'], indent=True, goal_owner=goal)
                    assigned_tasks.append(t)

        # 3. Uncategorized (FIXED: Uses internal variable to avoid leakage)
        uncategorized = [t for t in all_tasks if t not in assigned_tasks]
        if uncategorized:
            add_styled_item("<span style='color: #AA88FF;'>📦 UNCATEGORIZED</span>", is_header=True)
            for t in uncategorized:
                status_icon = "✅" if t["status"] == "complete" else "⬜"
                u_html = f"<span style='color:#666;'>⤷</span> {status_icon} {t['task']}"
                add_styled_item(u_html, raw_text=t['task'], indent=True)



    def add_project(self):
        """Dynamic tactical dialog for creating a brand new project."""
        data = {"project": "", "description": "", "deadline": "", "goals": [], "tasks": []} 
        
        # 1. Get the name first via tactical prompt
        name, ok = ghost_prompt(self, "INITIALIZE PLAN", "PROJECT NAME:")
        if not ok or not name: return
        
        # 2. Use TacticalDialog for the heavy lifting
        dialog = TacticalDialog(self, title=f"CONFIG: {name.upper()}", label="PROJECT PARAMETERS")
        dialog.input_field.hide()
        
        form_layout = QVBoxLayout()
        desc_input = QLineEdit(); desc_input.setPlaceholderText("Description..."); desc_input.setStyleSheet(STYLE_INPUT)
        date_input = QLineEdit(); date_input.setPlaceholderText("Deadline..."); date_input.setStyleSheet(STYLE_INPUT)
        
        form_layout.addWidget(QLabel("MISSION OBJECTIVE"))
        form_layout.addWidget(desc_input)
        form_layout.addWidget(QLabel("TIMELINE"))
        form_layout.addWidget(date_input)
        
        # Goals section with tactical styling
        main_layout = dialog.container.layout()
        main_layout.insertLayout(3, form_layout)
        
        if dialog.exec() == QDialog.Accepted:
            data["project"] = name.strip()
            data["description"] = desc_input.text().strip()
            data["deadline"] = date_input.text().strip()
            data["goals"] = ["General Operations"] # Default first goal

            if save_project_file(self.username, data, self.fernet):
                self.load_projects()
                # Auto-select the new project
                target_name = data["project"].replace(" ", "_").lower()
                for i in range(self.project_list.count()):
                    if self.project_list.item(i).text().lower() == target_name:
                        self.project_list.setCurrentRow(i)
                        self.display_project(self.project_list.item(i))
                        break

    def edit_task(self):
        """Replaced QInputDialog with Tactical Prompting"""
        if not hasattr(self, "current_project_data"): return
        selected_item = self.project_detail_list.currentItem()
        task_name = selected_item.data(Qt.UserRole) if selected_item else None
        
        if not task_name:
            ghost_alert(self, "SYSTEM", "NO TASK SELECTED")
            return

        task = next((t for t in self.current_project_data["tasks"] if t["task"] == task_name), None)
        if not task: return

        new_text, ok = ghost_prompt(self, "EDIT TASK", "REWRITE OBJECTIVE:", task["task"])
        if ok and new_text:
            task["task"] = new_text
            save_project_file(self.username, self.current_project_data, self.get_active_fernet(self.current_project_file))
            self.display_project(self.project_list.currentItem())

    def delete_task(self):
        """Replaced QMessageBox with ghost_alert"""
        if not hasattr(self, "current_project_data"): return
        selected_item = self.project_detail_list.currentItem()
        task_name = selected_item.data(Qt.UserRole) if selected_item else None
        
        if not task_name:
            ghost_alert(self, "SYSTEM", "SELECT TASK TO PURGE")
            return

        if ghost_alert(self, "CONFIRM PURGE", f"ERASE TASK: {task_name}?"):
            self.current_project_data["tasks"] = [t for t in self.current_project_data["tasks"] if t["task"] != task_name]
            save_project_file(self.username, self.current_project_data, self.get_active_fernet(self.current_project_file))
            self.display_project(self.project_list.currentItem())

    def delete_project(self):
        """Replaced QMessageBox with ghost_alert"""
        if not hasattr(self, "current_project_file"):
            ghost_alert(self, "SYSTEM", "NO PLAN SELECTED")
            return
            
        if ghost_alert(self, "DESTRUCT SEQUENCE", f"PERMANENTLY DELETE {self.current_project_file}?"):
            from project_manager import get_user_project_dir
            user_dir = get_user_project_dir(self.username)
            full_filepath = os.path.join(user_dir, self.current_project_file)
            
            if delete_project_file(full_filepath):
                self.load_projects()
                self.project_detail_list.clear()
                self.progress.setValue(0)
            else:
                ghost_alert(self, "ERROR", "FILE LOCK: COULD NOT DELETE")

    def mark_task_complete(self):
        """Toggles the completion status of the selected task."""
        if not hasattr(self, "current_project_data"):
            return

        selected_item = self.project_detail_list.currentItem()
        # Retrieve the raw task name stored in UserRole
        task_name = selected_item.data(Qt.UserRole) if selected_item else None

        if not task_name:
            ghost_alert(self, "SYSTEM", "SELECT A TASK TO COMPLETE")
            return

        # Find the task in the data and toggle status
        for task in self.current_project_data["tasks"]:
            if task["task"] == task_name:
                # Toggle: if complete -> incomplete, if incomplete -> complete
                task["status"] = "complete" if task["status"] == "incomplete" else "incomplete"
                break

        # Save and refresh the UI
        if save_project_file(self.username, self.current_project_data, self.fernet):
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

