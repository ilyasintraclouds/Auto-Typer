import sys
import time
import threading
import os

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QSpinBox, QSlider, QGroupBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QIcon
import pyautogui


class Signals(QObject):
    countdown_update = pyqtSignal(int)
    typing_finished = pyqtSignal()


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class AutoTyper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auto Typer")
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.resize(1000, 780)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e2e;
            }
            QLabel {
                color: #cdd6f4;
            }
            QTextEdit {
                background-color: #181825;
                color: #cdd6f4;
                border: 2px solid #313244;
                border-radius: 12px;
                font-family: 'Consolas', monospace;
                font-size: 15px;
                padding: 12px;
            }
            QGroupBox {
                border: 2px solid #313244;
                border-radius: 12px;
                background-color: #1e1e2e;
                margin-top: 10px;
                padding: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: #cba6f7;
                font-weight: bold;
            }
            QSpinBox {
                background-color: #181825;
                color: #cdd6f4;
                border: 2px solid #313244;
                border-radius: 8px;
                padding: 5px 8px;
                min-width: 110px;
            }
            QSlider::groove:horizontal {
                background: #313244;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #89b4fa;
                border: 2px solid #cdd6f4;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QPushButton {
                border-radius: 10px;
                padding: 14px;
                font-weight: bold;
                font-size: 15px;
            }
            QPushButton#startBtn {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QPushButton#stopBtn {
                background-color: #f38ba8;
                color: #1e1e2e;
            }
        """)
        
        self.signals = Signals()
        self.signals.countdown_update.connect(self.update_countdown)
        self.signals.typing_finished.connect(self.on_typing_finished)
        
        self.stop_flag = False
        self.typing_thread = None
        
        self.init_ui()
        pyautogui.FAILSAFE = True
    
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(25, 20, 25, 20)
        main.setSpacing(18)
        
        # Title
        title = QLabel("Auto Typer")
        title.setFont(QFont("Segoe UI", 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main.addWidget(title)
        
        # Text Area
        text_group = QGroupBox("Text to Type (formatting preserved)")
        text_layout = QVBoxLayout(text_group)
        text_layout.setContentsMargins(15, 20, 15, 15)
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Paste your code, commands, or text here...\n\nNew lines, tabs, and special characters are fully supported.")
        self.text_edit.setMinimumHeight(290)
        text_layout.addWidget(self.text_edit)
        main.addWidget(text_group)
        
        # Controls
        controls = QHBoxLayout()
        controls.setSpacing(16)
        
        # Initial Delay
        g1 = QGroupBox("Delay Before Starting")
        l1 = QHBoxLayout(g1)
        l1.setContentsMargins(15, 15, 15, 15)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 60)
        self.delay_spin.setValue(5)
        self.delay_spin.setSuffix(" sec")
        l1.addWidget(QLabel("Initial Delay:"))
        l1.addWidget(self.delay_spin)
        l1.addStretch()
        controls.addWidget(g1)
        
        # Line Delay
        g2 = QGroupBox("Delay After Each Line")
        l2 = QHBoxLayout(g2)
        l2.setContentsMargins(15, 15, 15, 15)
        self.line_delay_spin = QSpinBox()
        self.line_delay_spin.setRange(0, 300)
        self.line_delay_spin.setValue(0)
        self.line_delay_spin.setSuffix(" sec")
        l2.addWidget(QLabel("Per Line Delay:"))
        l2.addWidget(self.line_delay_spin)
        l2.addWidget(QLabel("(0 = No delay)"))
        l2.addStretch()
        controls.addWidget(g2)
        
        # Speed
        g3 = QGroupBox("Typing Speed")
        l3 = QHBoxLayout(g3)
        l3.setContentsMargins(15, 15, 15, 15)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 200)
        self.speed_slider.setValue(45)
        self.speed_slider.valueChanged.connect(self.update_speed_label)
        self.speed_label = QLabel("Fast")
        l3.addWidget(QLabel("Char Speed:"))
        l3.addWidget(self.speed_slider)
        l3.addWidget(self.speed_label)
        controls.addWidget(g3)
        
        main.addLayout(controls)
        
        # Countdown
        self.countdown_label = QLabel("Ready")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setFont(QFont("Segoe UI", 19, QFont.Bold))
        self.countdown_label.setStyleSheet("color: #a6e3a1; padding: 10px;")
        main.addWidget(self.countdown_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.start_btn = QPushButton("▶ Start Typing")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.setMinimumHeight(60)
        self.start_btn.clicked.connect(self.start_typing)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setMinimumHeight(60)
        self.stop_btn.clicked.connect(self.stop_typing)
        self.stop_btn.setEnabled(False)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        main.addLayout(btn_layout)
        
        # Status
        self.status_label = QLabel("Status: Idle")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #9399b2;")
        main.addWidget(self.status_label)
        
        # Tip
        tip = QLabel("Tip: Switch to target window after pressing Start. Move mouse to top-left corner for emergency stop.")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #9399b2; font-size: 13px;")
        main.addWidget(tip)
    
    def update_speed_label(self, val):
        if val < 30:   text = "Very Fast"
        elif val < 60: text = "Fast"
        elif val < 100: text = "Medium"
        elif val < 150: text = "Slow"
        else:          text = "Very Slow"
        self.speed_label.setText(text)
    
    def update_countdown(self, sec):
        if sec > 0:
            self.countdown_label.setText(f"Starting in {sec} seconds...")
            self.countdown_label.setStyleSheet("color: #fab387;")
        else:
            self.countdown_label.setText("Typing in progress...")
            self.countdown_label.setStyleSheet("color: #a6e3a1;")
    
    def start_typing(self):
        if not self.text_edit.toPlainText().strip():
            self.status_label.setText("Status: Please enter some text!")
            return
        self.stop_flag = False
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Status: Starting...")
        self.typing_thread = threading.Thread(target=self.typing_worker, daemon=True)
        self.typing_thread.start()
    
    def typing_worker(self):
        initial_delay = self.delay_spin.value()
        line_delay = self.line_delay_spin.value()
        
        for i in range(initial_delay, 0, -1):
            if self.stop_flag:
                self.signals.typing_finished.emit()
                return
            self.signals.countdown_update.emit(i)
            time.sleep(1)
        
        if self.stop_flag:
            self.signals.typing_finished.emit()
            return
        
        self.signals.countdown_update.emit(0)
        text = self.text_edit.toPlainText()
        char_interval = self.speed_slider.value() / 1000.0
        
        try:
            for char in text:
                if self.stop_flag:
                    break
                if char == '\n':
                    pyautogui.press('enter')
                    if line_delay > 0:
                        time.sleep(line_delay)
                elif char == '\t':
                    pyautogui.press('tab')
                else:
                    pyautogui.typewrite(char)
                time.sleep(char_interval)
        except:
            pass
        
        self.signals.typing_finished.emit()
    
    def stop_typing(self):
        self.stop_flag = True
        self.status_label.setText("Status: Stopping...")
    
    def on_typing_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.countdown_label.setText("Ready")
        self.countdown_label.setStyleSheet("color: #a6e3a1;")
        self.status_label.setText("Status: Idle" if not self.stop_flag else "Status: Stopped")


if __name__ == "__main__":
    pyautogui.PAUSE = 0.01
    app = QApplication(sys.argv)
    window = AutoTyper()
    window.show()
    sys.exit(app.exec_())