import sys, os, gc, importlib
import re
import random
import string

# --- Style Imports ---
from . import style_config
from .style_config import (
    FONT_FAMILY, FONT_SIZE,
    COLOR_BG, COLOR_FG, COLOR_ACCENT, COLOR_BUTTON, COLOR_PAGE_BG, COLOR_HIGHLIGHT, COLOR_PROTOCOL,
    STYLE_LABEL, STYLE_BUTTON
)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton,
    QHBoxLayout, QMessageBox, QInputDialog, QFileDialog, QLabel, QApplication,
    QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QEvent, QTimer
from PySide6.QtGui import QTextCursor, QTextOption, QFont, QPixmap

# --- System Imports ---
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Everything_else'))
from Everything_else.command_checker import check_for_commands
from Everything_else.jynx_operator_ui import execute_command, get_random_prompt
from Everything_else.model_registry import load_model_from_config, get_model_config, get_visual_description
from Everything_else.ai_council import run_council_streaming

# =====================================================================
# Workers (Normal & Council) - Logic Preserved
# =====================================================================
class StreamWorker(QObject):
    token_received = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, llm_fn, prompt, max_tokens=2048, temperature=0.7, image_path=None):
        super().__init__()
        self.llm_fn = llm_fn
        self.prompt = prompt
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.image_path = image_path 

    def run(self):
        try:
            for chunk in self.llm_fn(
                self.prompt, 
                max_tokens=self.max_tokens, 
                temperature=self.temperature,
                image_path=self.image_path
            ):
                token = ""
                if isinstance(chunk, dict):
                    choices = chunk.get("choices", [])
                    if choices:
                        choice = choices[0]
                        token = (choice.get("text", "") or 
                                 choice.get("delta", {}).get("content", "") or 
                                 choice.get("message", {}).get("content", ""))
                else:
                    token = str(chunk)
                if token:
                    self.token_received.emit(token)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class CouncilStreamWorker(QObject):
    token_received = Signal(object)
    finished = Signal()
    error = Signal(str)

    # Add username and fernet to the parentheses here:
    def __init__(self, user_prompt, image_path=None, username="Operator", fernet=None):
        super().__init__()
        self.user_prompt = user_prompt
        self.image_path = image_path
        self.username = username  # Now it knows what 'username' is
        self.fernet = fernet      # Now it knows what 'fernet' is

    def run(self):
        try:
            # This part is now perfect
            for event in run_council_streaming(
                self.user_prompt, 
                image_path=self.image_path, 
                username=self.username, 
                fernet=self.fernet
            ):
                self.token_received.emit(event)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

# =====================================================================
# Main ChatPage UI - THEME UPDATED
# =====================================================================
class ChatPage(QWidget):
    def __init__(self, username, passphrase, fernet, debug=False):
        super().__init__()
        self.username = username
        self.passphrase = passphrase
        self.fernet = fernet
        self.debug = debug 

        self.llm = None
        self.current_image_path = None 
        self.model_config = get_model_config("jynx_default")
        self.max_tokens = self.model_config.get("max_tokens", 4096)
        self.temperature = self.model_config.get("temperature", 0.7)

        self.setAcceptDrops(True)

        # Main Layout Setup
        self.main_layout = QVBoxLayout(self)

        # 1. Chat Area
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setFont(QFont(FONT_FAMILY, FONT_SIZE))
        self.main_layout.addWidget(self.chat_area)

        # 2. Status Row
        self.status_label = QLabel("● System Initializing...")
        self.main_layout.addWidget(self.status_label)

        self.loading_label = QLabel("")
        self.main_layout.addWidget(self.loading_label)

        # 3. Image Preview Area
        self.image_preview = QLabel()
        self.image_preview.setFixedHeight(100)
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.hide()
        self.main_layout.addWidget(self.image_preview)

        # 4. Input Box
        self.input_line = QTextEdit()
        self.input_line.installEventFilter(self)
        self.input_line.setPlaceholderText("Type a message and/or drop an image...")
        self.input_line.setFixedHeight(60)
        self.main_layout.addWidget(self.input_line)

        # 5. Buttons
        self.send_button = QPushButton("Send")
        self.send_button.setEnabled(False)
        self.send_button.clicked.connect(self.handle_prompt)

        self.protocol_button = QPushButton("Run Protocol")
        self.protocol_button.clicked.connect(self.manual_protocol_trigger)

        self.reason_button = QPushButton("Reason")
        self.reason_button.setEnabled(False)
        self.reason_button.clicked.connect(self.handle_reason)

        self.attach_btn = QPushButton("+")
        self.attach_btn.setFixedSize(35, 35)
        self.attach_btn.clicked.connect(self.open_file_dialog)

        self.btns = QHBoxLayout()
        self.btns.addWidget(self.attach_btn)
        self.btns.addWidget(self.send_button)
        self.btns.addWidget(self.protocol_button)
        self.btns.addWidget(self.reason_button)
        self.main_layout.addLayout(self.btns)

        # APPLY THEME INITIALLY
        self.apply_dynamic_theme()
        QTimer.singleShot(500, self.deferred_load)

    def showEvent(self, event):
        super().showEvent(event)
        self.apply_dynamic_theme()

    def apply_dynamic_theme(self, theme_dict=None):
        """Updates the UI colors using a theme dictionary instead of static files."""
        # Fallback to current config if no dict is provided
        if theme_dict is None:
            importlib.reload(style_config)
            theme_dict = {
                "COLOR_BG": style_config.COLOR_BG,
                "COLOR_FG": style_config.COLOR_FG,
                "COLOR_ACCENT": style_config.COLOR_ACCENT,
                "COLOR_BUTTON": style_config.COLOR_BUTTON,
                "COLOR_BORDER": getattr(style_config, "COLOR_BORDER", "#d1d1d1")
            }

        bg = theme_dict.get("COLOR_BG")
        fg = theme_dict.get("COLOR_FG")
        accent = theme_dict.get("COLOR_ACCENT")
        btn_base = theme_dict.get("COLOR_BUTTON")
        border = theme_dict.get("COLOR_BORDER", accent) # Use border if exists, else accent

        # 1. Main Page Background
        self.setStyleSheet(f"background-color: {bg}; border: none;")

        # 2. Chat & Input Areas (The text boxes)
        box_style = f"""
            QTextEdit {{
                background-color: {btn_base}; 
                color: {fg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 5px;
            }}
        """
        self.chat_area.setStyleSheet(box_style)
        self.input_line.setStyleSheet(box_style)
        self.chat_area.viewport().setStyleSheet("background: transparent;")
        self.input_line.viewport().setStyleSheet("background: transparent;")

        # 3. Status Labels
        self.status_label.setStyleSheet(f"color: {accent}; background: transparent;")

        # 4. The Buttons (The "Button Base" and "Accent" colors)
        button_style = f"""
            QPushButton {{
                background-color: {btn_base};
                color: {fg};
                border: 2px solid {border};
                padding: 8px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {accent};
                color: {bg}; 
            }}
            QPushButton:pressed {{
                background-color: {fg};
                color: {bg};
            }}
        """
        self.send_button.setStyleSheet(button_style)
        self.protocol_button.setStyleSheet(button_style)
        self.reason_button.setStyleSheet(button_style)
        self.attach_btn.setStyleSheet(button_style)

    # --- DRAG & DROP & ATTACHMENT ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.process_attachment(files[0])

    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if path:
            self.process_attachment(path)

    def process_attachment(self, path):
        importlib.reload(style_config)
        ext = path.lower()
        if ext.endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
            self.current_image_path = path
            pixmap = QPixmap(path)
            scaled = pixmap.scaledToHeight(90, Qt.SmoothTransformation)
            self.image_preview.setPixmap(scaled)
            self.image_preview.show()
            self.attach_btn.setStyleSheet(f"background-color: {style_config.COLOR_ACCENT}; color: {style_config.COLOR_BG}; font-weight: bold; border-radius: 5px;")
        else:
            self.input_line.insertPlainText(path)

    def clear_attachment(self):
        self.current_image_path = None
        self.image_preview.clear()
        self.image_preview.hide()
        self.apply_dynamic_theme() # Restore standard button style

    # --- CORE HANDLERS ---
    def handle_prompt(self):
        importlib.reload(style_config)
        prompt = self.input_line.toPlainText().strip()
        image_path = self.current_image_path
        
        if not prompt and not image_path: 
            return

        self.append_message("You", prompt if prompt else "")
        if image_path:
            self.append_image_to_chat(image_path)
        
        if image_path:
            self.handle_reason(is_auto_call=True) 
        else:
            self.chat_area.insertHtml(f"<br><b style='color:{style_config.COLOR_ACCENT};'>{self.model_config['name']}:</b> ")
            self.thread = QThread()
            self.worker = StreamWorker(
                self.llm, 
                prompt, 
                self.max_tokens, 
                self.temperature, 
                None 
            )
            self.worker.moveToThread(self.thread)
            self.worker.token_received.connect(self._append_streamed_token)
            self.worker.finished.connect(self.thread.quit)
            self.thread.started.connect(self.worker.run)
            self.thread.start()

        self.input_line.clear()
        self.clear_attachment()

    def append_image_to_chat(self, path):
        clean_path = path.replace("\\", "/")
        if not clean_path.startswith("file:///"):
            clean_path = f"file:///{clean_path}"
        image_html = f'<div style="margin: 10px 0;"><img src="{clean_path}" width="300"></div>'
        self.chat_area.append("") 
        self.chat_area.insertHtml(image_html)
        self.chat_area.moveCursor(QTextCursor.End)

    def append_message(self, sender, text):
        importlib.reload(style_config)
        color = style_config.COLOR_ACCENT if sender != "You" else style_config.COLOR_FG
        self.chat_area.append(f"<b style='color:{color};'>{sender}:</b> {text}")
        self.chat_area.moveCursor(QTextCursor.End)

    def handle_reason(self, is_auto_call=False):
        importlib.reload(style_config)
        prompt = self.input_line.toPlainText().strip()
        image_path = self.current_image_path

        if not is_auto_call:
            if not prompt and not image_path: return
            self.append_message("You", prompt if prompt else "")
            if image_path:
                self.append_image_to_chat(image_path)
            self.input_line.clear()
            self.clear_attachment()

        self.append_message("Council", "Summoning experts...\n")
        self.loading_label.setText("Reasoning...")
        
        self.reasoning_worker = CouncilStreamWorker(prompt, image_path, username=self.username, fernet=self.fernet)
        self.reasoning_thread = QThread()
        self.reasoning_worker.moveToThread(self.reasoning_thread)
        self.reasoning_worker.token_received.connect(self._handle_council_event)
        self.reasoning_worker.finished.connect(self.reasoning_thread.quit)
        self.reasoning_thread.started.connect(self.reasoning_worker.run)
        self.reasoning_thread.start()

    def _append_streamed_token(self, token):
        self.chat_area.insertPlainText(token)
        self.chat_area.moveCursor(QTextCursor.End)

    def _handle_council_event(self, event):
        importlib.reload(style_config)
        etype = event[0]
        
        if etype == "summary":
            if not hasattr(self, "_summary_started") or not self._summary_started:
                self.chat_area.insertHtml(f"<br><br><b style='color:{style_config.COLOR_PROTOCOL};'>Target:</b> ")
                self._summary_started = True
            self.chat_area.insertPlainText(event[1])
            
        elif etype == "expert_start":
            self._summary_started = False 
            self.chat_area.insertHtml(f"<br><br><b style='color:{style_config.COLOR_ACCENT};'>{event[1]}:</b><br>")
            
        elif etype == "expert_token":
            if len(event) >= 3: 
                self.chat_area.insertPlainText(event[2])
                
        elif etype == "verdict_start":
            self.chat_area.insertHtml(f"<br><br><b style='color:{style_config.COLOR_HIGHLIGHT};'>Final Verdict:</b><br>")
            
        elif etype == "verdict_token":
            self.chat_area.insertPlainText(event[1])
            
        elif etype == "done":
            self.chat_area.insertHtml(f"<br><br><small style='color:{style_config.COLOR_FG};'><i>[Council Concluded]</i></small><br>")
            self.loading_label.setText("")
            self.restore_default_model()
            
        self.chat_area.moveCursor(QTextCursor.End)

    def deferred_load(self):
        try:
            self.llm, _ = load_model_from_config("jynx_default")
            self.send_button.setEnabled(True)
            self.reason_button.setEnabled(True)
            self.status_label.setText("● AI Engine Online")
        except:
            self.status_label.setText("○ Offline")

    def restore_default_model(self):
        self.llm, self.model_config = load_model_from_config("jynx_default")
        gc.collect()

    def eventFilter(self, obj, event):
        if obj == self.input_line and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & Qt.ControlModifier:
                    self.handle_reason()
                else:
                    self.handle_prompt()
                return True
        return super().eventFilter(obj, event)

    # --- PROTOCOLS ---
    def manual_protocol_trigger(self):
        from Everything_else.jynx_operator_ui import soul_vent, soul_vent_summon
        protocol, ok = QInputDialog.getText(self, "Run Protocol", "Enter protocol name:")
        if not ok or not protocol: return

        if protocol == "soul_vent":
            filename, ok1 = QInputDialog.getText(self, "Soul Vent", "Journal filename:")
            if not ok1: return
            chosen_prompt = get_random_prompt()
            try:
                entry, ok2 = self.get_multiline_input("Soul Vent", "Write your entry:", f"{chosen_prompt}\n\n")
            except:
                entry, ok2 = QInputDialog.getMultiLineText(self, "Soul Vent", "Write:", f"{chosen_prompt}\n\n")
            
            if not ok2: return
            passphrase, ok3 = QInputDialog.getText(self, "Soul Vent", "Passphrase:", QLineEdit.Password)
            if ok3:
                try:
                    soul_vent(filename, entry, passphrase, chosen_prompt=chosen_prompt)
                    self.append_message("🔐 Soul Vent", "Encrypted.")
                except Exception as e: self.append_message("❌ Error", str(e))

        elif protocol == "soul_vent_summon":
            passphrase, ok1 = QInputDialog.getText(self, "Summon", "Passphrase:", QLineEdit.Password)
            if ok1:
                try:
                    filenames, decrypted_map = soul_vent_summon(passphrase)
                    if not filenames:
                        self.append_message("🧠 Soul Vent", decrypted_map)
                        return
                    selected, ok2 = QInputDialog.getItem(self, "Entry", "Choose:", filenames, 0, False)
                    if ok2 and selected: self._show_readonly_dialog(selected, decrypted_map[selected])
                except Exception as e: self.append_message("❌ Error", str(e))
        else:
            try:
                result = execute_command(protocol, username=self.username)
                self.append_message("⚙️ Protocol", result)
            except Exception as e: self.append_message("❌ Error", str(e))

    def _show_readonly_dialog(self, title, text):
        importlib.reload(style_config)
        dialog = QDialog(self)
        dialog.setWindowTitle(f"📖 {title}")
        layout = QVBoxLayout(dialog)
        text_display = QTextEdit()
        text_display.setPlainText(text)
        text_display.setReadOnly(True)
        text_display.setMinimumSize(600, 400)
        text_display.setStyleSheet(f"background-color: {style_config.COLOR_BG}; color: {style_config.COLOR_FG}; border: 1px solid {style_config.COLOR_ACCENT};")
        layout.addWidget(text_display)
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(style_config.STYLE_BUTTON)
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec()
        
    def get_multiline_input(self, title, label, initial_text=""):
        importlib.reload(style_config)
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(500)
        layout = QVBoxLayout(dialog)
        lbl = QLabel(label)
        lbl.setStyleSheet(style_config.STYLE_LABEL)
        layout.addWidget(lbl)
        text_edit = QTextEdit()
        text_edit.setPlainText(initial_text)
        text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        text_edit.setStyleSheet(f"background-color: {style_config.COLOR_BUTTON}; color: {style_config.COLOR_FG};")
        layout.addWidget(text_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.Accepted:
            return text_edit.toPlainText(), True
        return "", False