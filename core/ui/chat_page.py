import sys, os, gc, importlib
import re
import random
import string

from .style_config import (
    T, FONT_FAMILY, FONT_SIZE, 
    STYLE_BUTTON, STYLE_INPUT, STYLE_LABEL,
    COLOR_BG, COLOR_FG, COLOR_ACCENT, COLOR_BUTTON, 
    COLOR_HIGHLIGHT, COLOR_BORDER, COLOR_PROTOCOL, COLOR_PAGE_BG
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
from Everything_else.jynx_operator_ui import execute_command, get_random_prompt, soul_vent, soul_vent_summon
from Everything_else.model_registry import load_model_from_config, get_model_config, get_visual_description
from Everything_else.ai_council import run_council_streaming

# =====================================================================
# Workers (Logic Preserved & Hardened)
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
            if not self.llm_fn:
                raise Exception("LLM Engine not initialized.")
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

    def __init__(self, user_prompt, image_path=None, username="Operator", fernet=None):
        super().__init__()
        self.user_prompt = user_prompt
        self.image_path = image_path
        self.username = username 
        self.fernet = fernet 

    def run(self):
        try:
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
# Main ChatPage UI
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

        # --- ADD THESE LINES ---
        self.max_tokens = self.model_config.get("max_tokens", 2048)
        self.temperature = self.model_config.get("temperature", 0.7)
        
        self._active_thread = None
        self._active_worker = None

        self.setAcceptDrops(True)
        self.init_ui()
        QTimer.singleShot(500, self.deferred_load)

    def init_ui(self):
        # 1. Main Layout - Zero margins to stop the "box in a box" look
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 10, 20, 20)
        self.main_layout.setSpacing(10)

        # 2. Chat Area - No border, transparent background
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setFont(QFont(FONT_FAMILY, FONT_SIZE))
        self.chat_area.setObjectName("ChatDisplay") # We will style this in QSS
        self.main_layout.addWidget(self.chat_area)

        # 3. Status/Loading - Muted slate colors
        status_container = QHBoxLayout()
        self.status_label = QLabel("● SYSTEM INITIALIZING...")
        self.loading_label = QLabel("")
        status_container.addWidget(self.status_label)
        status_container.addStretch()
        status_container.addWidget(self.loading_label)
        self.main_layout.addLayout(status_container)

        self.image_preview = QLabel()
        self.image_preview.setFixedHeight(100)
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.hide()
        self.main_layout.addWidget(self.image_preview)

        # 4. Input Line - Use the specific ObjectName for consistent styling
        self.input_line = QTextEdit()
        self.input_line.installEventFilter(self)
        self.input_line.setPlaceholderText("TYPE MESSAGE OR DROP IMAGE...")
        self.input_line.setFixedHeight(80)
        self.input_line.setObjectName("ChatInput")
        self.main_layout.addWidget(self.input_line)

        # 5. UNIFIED BUTTONS (Fixes your size issue)
        self.btns = QHBoxLayout()
        self.btns.setSpacing(8) # Space between buttons
        
        # Attach Button (+)
        self.attach_btn = QPushButton("+")
        self.attach_btn.setObjectName("PlusBtn")
        
        # Main Actions
        self.send_button = QPushButton("SEND")
        self.protocol_button = QPushButton("PROTOCOL")
        self.reason_button = QPushButton("REASON")

        for b in [self.send_button, self.protocol_button, self.reason_button]:
            b.setObjectName("ChatActionBtn") # Force them to use the CSS rule
            b.setEnabled(False)
            self.btns.addWidget(b)
        
        # Insert the + at the start of the row
        self.btns.insertWidget(0, self.attach_btn)
        self.main_layout.addLayout(self.btns)

        # Connections
        self.attach_btn.clicked.connect(self.open_file_dialog)
        self.send_button.clicked.connect(self.handle_prompt)
        self.protocol_button.clicked.connect(self.manual_protocol_trigger)
        self.reason_button.clicked.connect(self.handle_reason)
        
        self.apply_dynamic_theme()

    def apply_dynamic_theme(self):
        """Removes hardcoded whites and enforces the theme dictionary."""
        self.setStyleSheet(f"background: transparent; border: none;")
        
        # Style the Text Boxes
        boxes = f"""
            QTextEdit#ChatDisplay, QTextEdit#ChatInput {{
                background-color: {T['BG_CARD']}; 
                border: 1px solid {T['BORDER']};
                border-radius: 8px;
                color: {T['TEXT_MAIN']};
                padding: 10px;
            }}
        """
        self.chat_area.setStyleSheet(boxes)
        self.input_line.setStyleSheet(boxes)

        self.status_label.setStyleSheet(f"color: {T['ACCENT']}; font-size: 10px; font-weight: bold;")
        self.loading_label.setStyleSheet(f"color: {T['SUCCESS']}; font-size: 10px;")

    def append_message(self, sender, text):
        """Standardizes message spacing with clear gaps between turns."""
        color = COLOR_ACCENT if sender != "You" else COLOR_FG
        # Added an extra <br> for a clean double-space between chat turns
        html = f"""
        <br><br>
        <span style='color:{color}; font-weight: bold;'>{sender.upper()}:</span>
        <span style='color:{COLOR_FG};'> {text}</span>
        """
        self.chat_area.insertHtml(html)
        self.chat_area.moveCursor(QTextCursor.End)

    def handle_prompt(self):
        prompt = self.input_line.toPlainText().strip()
        image_path = self.current_image_path
        if not prompt and not image_path: return
        
        self.append_message("You", prompt if prompt else "")
        
        if image_path: 
            self.append_image_to_chat(image_path)
            self.handle_reason(is_auto_call=True) 
        else:
            ai_name = self.model_config.get('name', 'JYNX').upper()
            # Added double <br> here to separate from the User Prompt above
            self.chat_area.insertHtml(f"<br><br><span style='color:{COLOR_ACCENT}; font-weight:bold;'>{ai_name}:</span> ")
            
            self._active_thread = QThread()
            self._active_worker = StreamWorker(self.llm, prompt, self.max_tokens, self.temperature)
            self._active_worker.moveToThread(self._active_thread)
            
            self._active_worker.token_received.connect(self._append_streamed_token)
            self._active_worker.error.connect(lambda e: self.append_message("SYSTEM", f"ERROR: {e}"))
            
            self._active_worker.finished.connect(self._active_thread.quit)
            self._active_worker.finished.connect(self._active_worker.deleteLater)
            self._active_thread.finished.connect(self._active_thread.deleteLater)
            
            self._active_thread.started.connect(self._active_worker.run)
            self._active_thread.start()
            
        self.input_line.clear()
        self.clear_attachment()

    def handle_reason(self, is_auto_call=False):
        prompt = self.input_line.toPlainText().strip()
        image_path = self.current_image_path

        if not is_auto_call:
            if not prompt and not image_path: return
            self.append_message("You", prompt if prompt else "")
            if image_path:
                self.append_image_to_chat(image_path)
            self.input_line.clear()
            self.clear_attachment()

        # Reset the summary tracker for the new council session
        self._summary_started = False 
        
        self.loading_label.setText("REASONING...")
        
        self._active_thread = QThread()
        self._active_worker = CouncilStreamWorker(prompt, image_path, username=self.username, fernet=self.fernet)
        self._active_worker.moveToThread(self._active_thread)
        
        self._active_worker.token_received.connect(self._handle_council_event)
        self._active_worker.error.connect(lambda e: self.append_message("SYSTEM", f"ERROR: {e}"))
        
        self._active_worker.finished.connect(self._active_thread.quit)
        self._active_worker.finished.connect(self._active_worker.deleteLater)
        self._active_thread.finished.connect(self._active_thread.deleteLater)
        
        self._active_thread.started.connect(self._active_worker.run)
        self._active_thread.start()

    def _handle_council_event(self, event):
        etype = event[0]
        self.chat_area.moveCursor(QTextCursor.End)
        
        if etype == "summary":
            if not getattr(self, "_summary_started", False):
                # Using COLOR_PROTOCOL (Tactical Amber) for the Target header
                self.chat_area.insertHtml(f"<br><br><b style='color:{COLOR_PROTOCOL};'>TARGET:</b> ")
                self._summary_started = True
            
            raw_token = str(event[1])
            clean_token = raw_token.replace("***SUMMARY***", "").replace("***EXPERTS***", "")
            if clean_token:
                self.chat_area.insertPlainText(clean_token)

        elif etype == "expert_start":
            self._summary_started = False 
            expert_name = str(event[1]).upper()
            # Use COLOR_FG (Off-White) to make Expert names pop against the Green/Dark BG
            self.chat_area.insertHtml(f"<br><br><b style='color:{COLOR_FG};'>{expert_name}:</b> ")
            
        elif etype == "expert_token":
            if len(event) >= 3:
                self.chat_area.insertPlainText(event[2])

        elif etype == "verdict_start":
            self.chat_area.insertHtml(f"<br><br><b style='color:{COLOR_PROTOCOL};'>FINAL VERDICT:</b> ")

        elif etype == "verdict_token":
            self.chat_area.insertPlainText(event[1])

        elif etype == "done":
            self.loading_label.setText("")
            self.chat_area.insertHtml("<br><br><small><i>[Council Concluded]</i></small><br>")
            self.restore_default_model()
            
        self.chat_area.moveCursor(QTextCursor.End)

    def _append_streamed_token(self, token):
        self.chat_area.insertPlainText(token)
        self.chat_area.moveCursor(QTextCursor.End)

    def deferred_load(self):
        try:
            self.llm, _ = load_model_from_config("jynx_default")
            self.send_button.setEnabled(True)
            self.reason_button.setEnabled(True)
            self.protocol_button.setEnabled(True)
            self.status_label.setText("● AI ENGINE ONLINE")
        except Exception as e:
            self.status_label.setText(f"○ OFFLINE: {str(e)}")

    def eventFilter(self, obj, event):
        if obj == self.input_line and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & Qt.ControlModifier:
                    self.handle_reason()
                else:
                    self.handle_prompt()
                return True
        return super().eventFilter(obj, event)

    # --- Standard Support Methods ---
    def process_attachment(self, path):
        if path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')):
            self.current_image_path = path
            pixmap = QPixmap(path).scaledToHeight(90, Qt.SmoothTransformation)
            self.image_preview.setPixmap(pixmap)
            self.image_preview.show()
            self.attach_btn.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: {COLOR_BG};")
        else:
            self.input_line.insertPlainText(path)

    def clear_attachment(self):
        self.current_image_path = None
        self.image_preview.hide()
        self.attach_btn.setStyleSheet(STYLE_BUTTON)

    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if path: self.process_attachment(path)

    def restore_default_model(self):
        self.llm, self.model_config = load_model_from_config("jynx_default")
        self.max_tokens = self.model_config.get("max_tokens", 2048)
        self.temperature = self.model_config.get("temperature", 0.7)
        gc.collect()


    def manual_protocol_trigger(self):
        protocol, ok = QInputDialog.getText(self, "Protocol", "ID:")
        if not ok or not protocol: return
        
        if protocol == "soul_vent":
            fname, ok1 = QInputDialog.getText(self, "Soul Vent", "Journal ID:")
            if not ok1: return
            pmp = get_random_prompt()
            entry, ok2 = self.get_multiline_input("Soul Vent", "INPUT:", f"{pmp}\n\n")
            if not ok2: return
            key, ok3 = QInputDialog.getText(self, "Soul Vent", "Key:", QLineEdit.Password)
            if ok3:
                try:
                    soul_vent(fname, entry, key, chosen_prompt=pmp)
                    self.append_message("Soul Vent", "ENCRYPTED.")
                except Exception as e: self.append_message("Error", str(e))
        elif protocol == "soul_vent_summon":
            key, ok1 = QInputDialog.getText(self, "Summon", "Key:", QLineEdit.Password)
            if ok1:
                try:
                    fnames, dmap = soul_vent_summon(key)
                    if not fnames: return
                    sel, ok2 = QInputDialog.getItem(self, "Entry", "SELECT ID:", fnames, 0, False)
                    if ok2: self._show_readonly_dialog(sel, dmap[sel])
                except Exception as e: self.append_message("Error", str(e))
        else:
            try:
                res = execute_command(protocol, username=self.username)
                self.append_message("Protocol", res)
            except Exception as e: self.append_message("Error", str(e))

    def _show_readonly_dialog(self, title, text):
        d = QDialog(self)
        d.setWindowTitle(title)
        l = QVBoxLayout(d)
        te = QTextEdit()
        te.setPlainText(text)
        te.setReadOnly(True)
        te.setStyleSheet(STYLE_INPUT)
        l.addWidget(te)
        b = QPushButton("CLOSE")
        b.setStyleSheet(STYLE_BUTTON)
        b.clicked.connect(d.accept)
        l.addWidget(b)
        d.exec()

    def get_multiline_input(self, title, label, initial_text=""):
        d = QDialog(self)
        d.setWindowTitle(title)
        l = QVBoxLayout(d)
        l.addWidget(QLabel(label))
        te = QTextEdit()
        te.setPlainText(initial_text)
        te.setStyleSheet(STYLE_INPUT)
        l.addWidget(te)
        ok = QPushButton("OK")
        ok.clicked.connect(d.accept)
        l.addWidget(ok)
        if d.exec() == QDialog.Accepted: return te.toPlainText(), True
        return "", False