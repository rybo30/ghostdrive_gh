# ui/profile_page.py
import json, os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QLabel, QPushButton, 
    QFormLayout, QFrame, QSlider, QHBoxLayout, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from .style_config import (
    COLOR_BG, COLOR_FG, COLOR_ACCENT, COLOR_BUTTON, 
    COLOR_PROTOCOL, COLOR_PAGE_BG, STYLE_BUTTON, FONT_SIZE, FONT_FAMILY
)

class ProfilePage(QWidget):
    theme_changed = Signal(dict)

    def __init__(self, username, fernet):
        super().__init__()
        self.username = username
        self.fernet = fernet
        
        # --- USB-SAFE PATHING ---
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.profile_dir = os.path.join(base_dir, "Everything_else", "vault")
        if not os.path.exists(self.profile_dir):
            self.profile_dir = os.path.join(base_dir, "core", "Everything_else", "vault")
            
        self.profile_path = os.path.join(self.profile_dir, f"{username}_profile.enc")
        
        self.current_theme = {
            "COLOR_BG": COLOR_BG, "COLOR_FG": COLOR_FG,
            "COLOR_ACCENT": COLOR_ACCENT, "COLOR_BUTTON": COLOR_BUTTON,
            "COLOR_PROTOCOL": COLOR_PROTOCOL, "COLOR_PAGE_BG": COLOR_PAGE_BG,
            "COLOR_BORDER": "#e0e0e0" 
        }

        self.setup_ui()
        self.load_profile()

    def setup_ui(self):
        # Main container with breathing room
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(15)

        # 1. Header Section (Matching Project Manager Style)
        header_layout = QVBoxLayout()
        self.title_label = QLabel("NEURAL MAPPING & INTERFACE")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(f"""
            color: {COLOR_FG}; 
            font-size: {FONT_SIZE + 10}px; 
            font-weight: 800; 
            letter-spacing: 1px;
            margin-bottom: 5px;
        """)
        header_layout.addWidget(self.title_label)
        
        # The Divider Line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {COLOR_ACCENT}; min-height: 2px; max-height: 2px;")
        header_layout.addWidget(line)
        
        main_layout.addLayout(header_layout)

        # 2. Scroll Area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(content_widget)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(25)

        # --- SECTION HELPER ---
        def create_card(title):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: white;
                    border-radius: 15px;
                    border: 1px solid #e0e0e0;
                }}
                QLabel {{ border: none; font-weight: bold; color: #444; }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(20, 20, 20, 20)
            
            header = QLabel(title)
            header.setStyleSheet(f"color: {COLOR_ACCENT}; font-size: 14px; text-transform: uppercase;")
            card_layout.addWidget(header)
            card_layout.addSpacing(10)
            return card, card_layout

        # --- OPERATOR HEURISTICS CARD ---
        heur_card, heur_layout = create_card("Operator Personal Heuristics")
        
        # 1. ADD THE AI COUNCIL NOTE HERE
        council_note = QLabel("The AI Council specifically requested we ask you these questions.")
        council_note.setStyleSheet(f"color: {COLOR_ACCENT}; font-style: italic; font-size: 11px; margin-bottom: 5px;")
        heur_layout.addWidget(council_note)

        h_form = QFormLayout()
        h_form.setSpacing(15) # Increased spacing for better readability
        h_form.setLabelAlignment(Qt.AlignLeft)

        # Define the input style (Keeping your original look)
        input_style = f"""
            QLineEdit {{
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 10px;
                background: #fcfcfc;
                font-family: '{FONT_FAMILY}';
                font-size: 13px;
            }}
            QLineEdit:focus {{ border: 2px solid {COLOR_ACCENT}; background: white; }}
        """

        # 2. CREATE THE INPUTS INDIVIDUALLY FOR CUSTOMIZATION
        self.h_inputs = {
            "callsign": QLineEdit(),
            "region": QLineEdit(),
            "goal": QLineEdit(),
            "fear": QLineEdit(),
            "logic": QLineEdit()
        }

        # Apply style and set placeholders (The "Examples")
        self.h_inputs["callsign"].setPlaceholderText("e.g., Ghost_Zero, Neon_Specter")
        self.h_inputs["region"].setPlaceholderText("e.g., Sector 7G, North America")
        self.h_inputs["goal"].setPlaceholderText("e.g., To build a sustainable tech-farm and achieve autonomy.")
        self.h_inputs["fear"].setPlaceholderText("e.g., Total data corruption or loss of family.")
        self.h_inputs["logic"].setPlaceholderText("e.g., Intuitive / Big-picture")

        # 3. ADD TO FORM WITH THE NEW QUESTIONS
        h_form.addRow(QLabel("What is your Operator Callsign?"), self.h_inputs["callsign"])
        h_form.addRow(QLabel("Where are you currently located?"), self.h_inputs["region"])
        h_form.addRow(QLabel("What are your primary life goals?"), self.h_inputs["goal"])
        h_form.addRow(QLabel("What is your greatest fear?"), self.h_inputs["fear"])
        h_form.addRow(QLabel("How do you like to receive information?"), self.h_inputs["logic"])

        # Apply the style to all of them
        for widget in self.h_inputs.values():
            widget.setStyleSheet(input_style)

        heur_layout.addLayout(h_form)
        self.layout.addWidget(heur_card)

        # --- VISUAL TONE CARD ---
        tone_card, tone_layout = create_card("System Visual Tone")
        
        # Sliders Container
        slider_box = QVBoxLayout()
        slider_box.setSpacing(15)

        self.sat_slider = QSlider(Qt.Horizontal)
        self.val_slider = QSlider(Qt.Horizontal)
        for s in [self.sat_slider, self.val_slider]:
            s.setRange(0, 255)
            s.setValue(127)
            s.setFixedHeight(20)

        slider_box.addWidget(QLabel("Saturation (Color Intensity)"))
        slider_box.addWidget(self.sat_slider)
        slider_box.addWidget(QLabel("Brightness (Luminance)"))
        slider_box.addWidget(self.val_slider)
        
        tone_layout.addLayout(slider_box)
        self.layout.addWidget(tone_card)

        # --- COLOR SPECTRUM CARD ---
        spec_card, spec_layout = create_card("Accent Color Palette")
        
        hue_style = """
            QSlider::groove:horizontal {
                height: 12px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                stop:0 red, stop:0.16 orange, stop:0.33 yellow, 
                stop:0.5 green, stop:0.66 blue, stop:0.83 indigo, stop:1 violet);
                border-radius: 6px;
            }
            QSlider::handle:horizontal {
                background: white; border: 1px solid #888; width: 20px; height: 20px; 
                margin: -5px 0; border-radius: 10px;
            }
        """

        self.sliders = {}
        for label_text, key in [("Accent Focus", "COLOR_ACCENT"), ("Interaction Surface", "COLOR_BUTTON")]:
            spec_layout.addWidget(QLabel(label_text))
            s = QSlider(Qt.Horizontal)
            s.setRange(0, 359)
            s.setStyleSheet(hue_style)
            s.valueChanged.connect(self.sync_theme)
            spec_layout.addWidget(s)
            self.sliders[key] = s

        self.layout.addWidget(spec_card)
        self.layout.addStretch()

        # --- FOOTER BUTTONS ---
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 20, 0, 0)
        
        self.reset_btn = QPushButton("Reset Defaults")
        self.reset_btn.setStyleSheet("color: #777; border: none; font-weight: bold;")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        
        self.save_btn = QPushButton("Commit Changes")
        self.save_btn.setFixedSize(220, 45)
        self.save_btn.setStyleSheet(STYLE_BUTTON + "font-size: 14px; border-radius: 12px;")
        self.save_btn.clicked.connect(self.save_profile)
        
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        
        main_layout.addWidget(scroll)
        main_layout.addLayout(btn_layout)

        scroll.setWidget(content_widget)
        self.sat_slider.valueChanged.connect(self.sync_theme)
        self.val_slider.valueChanged.connect(self.sync_theme)

    # ... [Keep sync_theme, save_profile, load_profile as they are] ...

    def sync_theme(self):
        s_val = self.sat_slider.value()
        v_val = self.val_slider.value()
        for key, slider in self.sliders.items():
            color = QColor.fromHsv(slider.value(), s_val, v_val)
            self.current_theme[key] = color.name()
        
        b_val = 200 if v_val < 128 else 60
        self.current_theme["COLOR_BORDER"] = QColor(b_val, b_val, b_val).name()
        self.theme_changed.emit(self.current_theme)

    def save_profile(self):
        data = {
            "heuristics": {k: w.text() for k, w in self.h_inputs.items()},
            "theme": self.current_theme,
            "slider_positions": {k: s.value() for k, s in self.sliders.items()},
            "sat": self.sat_slider.value(),
            "val": self.val_slider.value()
        }
        try:
            os.makedirs(self.profile_dir, exist_ok=True)
            encrypted = self.fernet.encrypt(json.dumps(data).encode())
            with open(self.profile_path, "wb") as f:
                f.write(encrypted)
            self.save_btn.setText("Profile Committed")
        except Exception as e:
            QMessageBox.critical(self, "Profile Error", f"Encryption failed: {e}")

    def load_profile(self):
        if not os.path.exists(self.profile_path):
            self.reset_to_defaults()
            return
        try:
            with open(self.profile_path, "rb") as f:
                decrypted = self.fernet.decrypt(f.read())
                data = json.loads(decrypted)
                
                heuristics = data.get("heuristics", {})
                for key, widget in self.h_inputs.items():
                    widget.setText(heuristics.get(key, ""))

                self.sat_slider.blockSignals(True)
                self.val_slider.blockSignals(True)
                self.sat_slider.setValue(data.get("sat", 127))
                self.val_slider.setValue(data.get("val", 127))
                
                positions = data.get("slider_positions", {})
                for key, val in positions.items():
                    if key in self.sliders:
                        self.sliders[key].blockSignals(True)
                        self.sliders[key].setValue(val)
                        self.sliders[key].blockSignals(False)
                
                self.sat_slider.blockSignals(False)
                self.val_slider.blockSignals(False)
                self.sync_theme()
        except Exception:
            self.reset_to_defaults()

    def reset_to_defaults(self):
        for widget in self.h_inputs.values():
            widget.clear()
        self.sat_slider.setValue(127)
        self.val_slider.setValue(200)
        if "COLOR_ACCENT" in self.sliders: self.sliders["COLOR_ACCENT"].setValue(200)
        if "COLOR_BUTTON" in self.sliders: self.sliders["COLOR_BUTTON"].setValue(200)
        self.sync_theme()