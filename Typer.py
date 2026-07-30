import sys
import time
import threading
import os
import logging
import subprocess
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QSpinBox, QSlider, QGroupBox,
    QCheckBox, QSizePolicy, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QIcon
import pyautogui


class Signals(QObject):
    countdown_update = pyqtSignal(int)
    typing_finished = pyqtSignal()


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class AutoTyper(QMainWindow):
    AUTO_CLOSE_PAIRS = {
        '(': ')',
        '{': '}',
        '[': ']',
        '"': '"',
    }
    AUTO_INDENT_CHARS = {'(', '{', '[', ':'}

    LANG_INDENT = {
        "Python": 4,
        "JavaScript": 2,
        "TypeScript": 2,
        "React (JSX)": 2,
        "Java": 4,
        "C": 4,
        "C++": 4,
        "SQL": 4,
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auto Typer")
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.resize(1000, 750)

        self.setup_logging()
        self.init_ui()

        self.signals = Signals()
        self.signals.countdown_update.connect(self.update_countdown)
        self.signals.typing_finished.connect(self.on_typing_finished)

        self.stop_flag = False
        self.typing_thread = None
        self.indent_size = 4
        self.use_tabs = False
        pyautogui.FAILSAFE = True

    def setup_logging(self):
        self.log_dir = os.path.join(os.path.expanduser("~"), "AutoTyper_Logs")
        os.makedirs(self.log_dir, exist_ok=True)
        log_file = os.path.join(self.log_dir, f"autotyper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler(log_file, encoding='utf-8')]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("AutoTyper started")

    def log(self, msg):
        if self.detailed_logging.isChecked():
            self.logger.info(msg)

    def open_logs_folder(self):
        if sys.platform == 'win32':
            os.startfile(self.log_dir)
        elif sys.platform == 'darwin':
            subprocess.run(['open', self.log_dir])
        else:
            subprocess.run(['xdg-open', self.log_dir])

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e2e; }
            QLabel {
                color: #cdd6f4;
                font-family: 'Segoe UI', sans-serif;
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
                margin-top: 8px;
                padding: 8px;
                font-weight: bold;
                color: #cba6f7;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: #cba6f7;
            }
            QSpinBox, QComboBox {
                background-color: #181825;
                color: #cdd6f4;
                border: 2px solid #313244;
                border-radius: 8px;
                padding: 4px 6px;
                min-width: 90px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #cdd6f4;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #181825;
                color: #cdd6f4;
                selection-background-color: #45475a;
            }
            QSlider::groove:horizontal {
                background: #313244;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #89b4fa;
                border: 2px solid #cdd6f4;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QPushButton {
                border-radius: 10px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
                color: #1e1e2e;
            }
            QPushButton#startBtn {
                background-color: #89b4fa;
            }
            QPushButton#startBtn:hover {
                background-color: #b4befe;
            }
            QPushButton#startBtn:pressed {
                background-color: #74c7ec;
            }
            QPushButton#startBtn:disabled {
                background-color: #45475a;
                color: #9399b2;
            }
            QPushButton#stopBtn {
                background-color: #f38ba8;
            }
            QPushButton#stopBtn:hover {
                background-color: #eba0ac;
            }
            QPushButton#stopBtn:pressed {
                background-color: #f5c2e7;
            }
            QPushButton#stopBtn:disabled {
                background-color: #45475a;
                color: #9399b2;
            }
            QPushButton#logBtn {
                background-color: #a6e3a1;
                color: #1e1e2e;
                padding: 6px 14px;
                font-size: 12px;
                border-radius: 8px;
            }
            QPushButton#logBtn:hover {
                background-color: #b4f0b0;
            }
            QCheckBox {
                color: #cdd6f4;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 2px solid #585b70;
                background-color: #181825;
            }
            QCheckBox::indicator:checked {
                background-color: #89b4fa;
                border: 2px solid #89b4fa;
            }
            QCheckBox::indicator:hover {
                border: 2px solid #89b4fa;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(20, 15, 20, 15)
        main.setSpacing(12)

        title = QLabel("Auto Typer")
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #cba6f7;")
        main.addWidget(title)

        subtitle = QLabel("Smart Code Typing with VS Code Integration")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #9399b2; margin-bottom: 6px;")
        main.addWidget(subtitle)

        text_group = QGroupBox("Text to Type")
        text_layout = QVBoxLayout(text_group)
        self.text_edit = QTextEdit()
        self.text_edit.setMinimumHeight(240)
        self.text_edit.setPlaceholderText("Paste your code here...")
        text_layout.addWidget(self.text_edit)
        main.addWidget(text_group)

        controls = QHBoxLayout()
        controls.setSpacing(10)

        g1 = QGroupBox("Initial Delay")
        l1 = QHBoxLayout(g1)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 60)
        self.delay_spin.setValue(5)
        self.delay_spin.setSuffix(" sec")
        l1.addWidget(QLabel("Delay:"))
        l1.addWidget(self.delay_spin)
        controls.addWidget(g1)

        g2 = QGroupBox("Line Delay")
        l2 = QHBoxLayout(g2)
        self.line_delay_spin = QSpinBox()
        self.line_delay_spin.setRange(0, 300)
        self.line_delay_spin.setValue(0)
        self.line_delay_spin.setSuffix(" sec")
        l2.addWidget(QLabel("After each line:"))
        l2.addWidget(self.line_delay_spin)
        controls.addWidget(g2)

        g3 = QGroupBox("Typing Speed")
        l3 = QHBoxLayout(g3)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 200)
        self.speed_slider.setValue(45)
        self.speed_slider.setMinimumWidth(160)
        self.speed_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.speed_slider.valueChanged.connect(self.update_speed_label)
        self.speed_label = QLabel("Fast")
        l3.addWidget(QLabel("Char Speed:"))
        l3.addWidget(self.speed_slider)
        l3.addWidget(self.speed_label)
        controls.addWidget(g3)
        main.addLayout(controls)

        options = QHBoxLayout()
        options.setSpacing(10)

        g4 = QGroupBox("Language Preset")
        l4 = QHBoxLayout(g4)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(sorted(self.LANG_INDENT.keys()))
        self.lang_combo.setCurrentText("Python")
        self.lang_combo.currentTextChanged.connect(self.on_language_changed)
        l4.addWidget(QLabel("Language:"))
        l4.addWidget(self.lang_combo)
        self.indent_info_label = QLabel("(4 spaces)")
        self.indent_info_label.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        l4.addWidget(self.indent_info_label)
        options.addWidget(g4)

        g5 = QGroupBox("Features")
        l5 = QVBoxLayout(g5)
        self.handle_autoclose = QCheckBox("Handle auto-closing brackets (Right Arrow to exit)")
        self.handle_autoclose.setChecked(True)
        l5.addWidget(self.handle_autoclose)
        self.handle_indent = QCheckBox("Handle auto-indentation (space-based adjustment)")
        self.handle_indent.setChecked(True)
        l5.addWidget(self.handle_indent)
        self.detailed_logging = QCheckBox("Enable detailed logging (to file)")
        self.detailed_logging.setChecked(False)
        l5.addWidget(self.detailed_logging)
        self.shift_enter = QCheckBox("Use Shift+Enter for new lines (chat apps: avoids sending)")
        self.shift_enter.setChecked(False)
        l5.addWidget(self.shift_enter)
        options.addWidget(g5)

        log_btn = QPushButton("📂 Open Logs")
        log_btn.setObjectName("logBtn")
        log_btn.setCursor(Qt.PointingHandCursor)
        log_btn.clicked.connect(self.open_logs_folder)
        options.addWidget(log_btn)

        main.addLayout(options)

        self.countdown_label = QLabel("Ready")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setFont(QFont("Segoe UI", 15, QFont.Bold))
        self.countdown_label.setStyleSheet("color: #a6e3a1; padding: 6px;")
        main.addWidget(self.countdown_label)

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ Start Typing")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_typing)
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(self.stop_typing)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        main.addLayout(btn_layout)

        self.status_label = QLabel("Status: Idle")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #9399b2;")
        main.addWidget(self.status_label)

        self.on_language_changed(self.lang_combo.currentText())

    def on_language_changed(self, lang):
        self.indent_size = self.LANG_INDENT.get(lang, 4)
        self.indent_info_label.setText(f"({self.indent_size} spaces)")
        self.log(f"Language set to {lang}, indent size = {self.indent_size}")

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
        self.log("--- New typing session ---")
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

        handle_autoclose = self.handle_autoclose.isChecked()
        handle_indent = self.handle_indent.isChecked()
        shift_enter = self.shift_enter.isChecked()
        self.use_tabs = False

        self._type_text(text, line_delay, handle_autoclose, handle_indent, shift_enter)

        self.signals.typing_finished.emit()

    def _type_text(self, text, line_delay, handle_autoclose, handle_indent, shift_enter=False):
        char_interval = self.speed_slider.value() / 1000.0
        lines = text.splitlines()

        pending_closes = []
        current_indent_str = ""

        for line_idx, line in enumerate(lines):
            if self.stop_flag:
                return

            original_indent = self._get_indentation(line)

            # Only strip the leading whitespace when _adjust_indentation is the
            # one writing it. With indentation handling off this must stay a
            # verbatim passthrough: every character, indentation included.
            content = line.lstrip(' \t') if handle_indent else line
            is_empty = (content == "")

            if not is_empty:
                if handle_autoclose:
                    self._type_content_with_autoclose(content, char_interval, pending_closes)
                else:
                    for ch in content:
                        if self.stop_flag:
                            return
                        pyautogui.write(ch)
                        time.sleep(char_interval)

            if line_idx < len(lines) - 1:
                if shift_enter:
                    pyautogui.hotkey('shift', 'enter')
                    self.log(f"Line {line_idx+1}: pressed Shift+Enter")
                else:
                    pyautogui.press('enter')
                    self.log(f"Line {line_idx+1}: pressed Enter")

                if handle_indent:
                    time.sleep(0.2)  # Give VS Code time to auto‑indent
                    next_line = lines[line_idx + 1]
                    next_indent = self._get_indentation(next_line)

                    last_non_space = line.rstrip(' \t')
                    triggers_indent = last_non_space and last_non_space[-1] in self.AUTO_INDENT_CHARS
                    if triggers_indent:
                        auto_indent = current_indent_str + " " * self.indent_size
                        self.log(f"  Line ends with '{last_non_space[-1]}', VS Code auto-indented")
                    else:
                        auto_indent = current_indent_str

                    self.log(f"  auto_indent = '{auto_indent}' (len={len(auto_indent)})")
                    self.log(f"  next_indent = '{next_indent}' (len={len(next_indent)})")

                    self._adjust_indentation(auto_indent, next_indent, char_interval)
                    current_indent_str = next_indent
                else:
                    current_indent_str = original_indent

                if line_delay > 0:
                    time.sleep(line_delay)

    def _get_indentation(self, line):
        indent = ""
        for ch in line:
            if ch in (' ', '\t'):
                indent += ch
            else:
                break
        return indent

    def _indent_level(self, indent_str):
        return len(indent_str) // self.indent_size if self.indent_size > 0 else 0

    def _adjust_indentation(self, current_indent, target_indent, char_interval):
        # Character counts, not levels: an indent that is not a whole multiple
        # of indent_size (aligned continuation lines) must survive intact.
        delta = len(target_indent) - len(current_indent)

        self.log(f"  Indent adjust: current={len(current_indent)}, target={len(target_indent)}, delta={delta}")

        if delta == 0:
            return

        # No End here. Straight after Enter the caret already sits at the end of
        # the auto-indent, and End would jump it past anything VS Code pushed
        # down onto this line (an auto-closed ), } or the tail of a docstring).

        if delta < 0:
            # Shift+Left selects exactly one character each press, then a single
            # Backspace deletes the selection. Pressing Backspace once per space
            # instead would delete a whole tab stop per press under
            # editor.useTabStops (a VS Code default) and blow past column 0.
            for _ in range(-delta):
                pyautogui.hotkey('shift', 'left')
                time.sleep(char_interval * 0.2)
            pyautogui.press('backspace')
            time.sleep(0.02)
            self.log(f"  Removed {-delta} char(s) (Shift+Left x{-delta}, Backspace)")
        else:
            pyautogui.write(' ' * delta)
            time.sleep(char_interval * 0.5)
            self.log(f"  Added {delta} space(s)")

    def _type_content_with_autoclose(self, content, char_interval, pending_closes):
        i = 0
        length = len(content)

        while i < length:
            if self.stop_flag:
                return

            in_comment, in_string, string_char, in_triple = self._is_comment_or_string(content, i)
            ch = content[i]

            if not in_comment and not in_string and not in_triple:
                if i + 2 < length and content[i:i+3] in ('"""', "'''"):
                    pyautogui.write(content[i:i+3])
                    self.log("  Typed triple quote")
                    time.sleep(char_interval * 3)
                    i += 3
                    continue

            if in_comment or in_string or in_triple:
                pyautogui.write(ch)
                time.sleep(char_interval)
                i += 1
                continue

            if ch in self.AUTO_CLOSE_PAIRS:
                close_char = self.AUTO_CLOSE_PAIRS[ch]
                pending_closes.append(close_char)
                pyautogui.write(ch)
                self.log(f"  Typed opening '{ch}' (pending: {pending_closes})")
                time.sleep(char_interval)
                i += 1
            elif ch in (')', '}', ']', '"'):
                if pending_closes and pending_closes[-1] == ch:
                    pending_closes.pop()
                    pyautogui.press('right')
                    self.log(f"  Right Arrow for auto-closed '{ch}'")
                    time.sleep(char_interval)
                    i += 1
                else:
                    pyautogui.write(ch)
                    time.sleep(char_interval)
                    i += 1
            else:
                pyautogui.write(ch)
                time.sleep(char_interval)
                i += 1

    def _is_comment_or_string(self, line, pos):
        in_comment = False
        in_string = False
        string_char = None
        in_triple = False
        escaped = False
        i = 0
        while i < len(line) and i <= pos:
            ch = line[i]
            if not in_comment and not in_string and not in_triple:
                if ch == '#':
                    in_comment = True
                    break
                if i + 2 < len(line) and line[i:i+3] in ('"""', "'''"):
                    in_triple = True
                    string_char = line[i:i+3]
                    i += 2
                elif ch in ('"', "'"):
                    in_string = True
                    string_char = ch
            elif in_triple and not escaped:
                if i + 2 < len(line) and line[i:i+3] == string_char:
                    in_triple = False
                    i += 2
            elif in_string and not escaped:
                if ch == string_char:
                    in_string = False
            escaped = (ch == '\\' and not escaped)
            i += 1
        return in_comment, in_string, string_char, in_triple

    def stop_typing(self):
        self.stop_flag = True
        self.status_label.setText("Status: Stopping...")
        self.log("Stop requested")

    def on_typing_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.countdown_label.setText("Ready")
        self.countdown_label.setStyleSheet("color: #a6e3a1;")
        self.status_label.setText("Status: Idle" if not self.stop_flag else "Status: Stopped")
        self.log("Typing session ended")


if __name__ == "__main__":
    pyautogui.PAUSE = 0.01
    app = QApplication(sys.argv)
    window = AutoTyper()
    window.show()
    sys.exit(app.exec_())