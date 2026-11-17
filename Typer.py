import sys
import time
import threading
import os
import json
import logging
import subprocess
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QSpinBox, QSlider, QGroupBox,
    QCheckBox, QSizePolicy, QComboBox, QShortcut
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QPoint
from PyQt5.QtGui import (
    QFont, QIcon, QKeySequence, QPixmap, QPainter, QColor, QPolygon
)
import pyautogui
import plain_text_sol
import python_sol
import tags


# Shown in the title bar, and checked against the release tag by the build
# workflow: bump this in the release commit, then tag it vMAJOR.MINOR.PATCH.
VERSION = "2.3.0"


class Signals(QObject):
    countdown_update = pyqtSignal(int)
    typing_finished = pyqtSignal()
    status_update = pyqtSignal(str)
    keys_used = pyqtSignal(str)


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
        "Plain Text": 0,  # Plain text with no indentation
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
        self.setWindowTitle(f"Auto Typer v{VERSION}")
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.resize(1000, 750)

        self.setup_logging()
        self.recent_keys = self.load_recent_keys()
        self.init_ui()

        self.signals = Signals()
        self.signals.countdown_update.connect(self.update_countdown)
        self.signals.typing_finished.connect(self.on_typing_finished)
        self.signals.status_update.connect(self.update_status)
        self.signals.keys_used.connect(self.on_keys_used)

        self.stop_flag = False
        self.typing_thread = None
        self.current_line = 0
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

    def report(self, msg):
        self.signals.status_update.emit(msg)

    def report_line(self, number):
        self.current_line = number
        self.signals.status_update.emit(f"Executing line {number}...")

    def report_wait(self, seconds):
        unit = "second" if seconds == 1 else "seconds"
        self.signals.status_update.emit(
            f"Executing line {self.current_line}... "
            f"Waiting for {seconds} {unit}..."
        )

    def remember_keys(self, label):
        self.signals.keys_used.emit(label)

    def recent_keys_path(self):
        base = (
            os.environ.get("LOCALAPPDATA")
            or os.environ.get("APPDATA")
            or os.path.expanduser("~")
        )
        folder = os.path.join(base, "AutoTyper")
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, "recent_keys.json")

    def load_recent_keys(self):
        try:
            with open(self.recent_keys_path(), encoding="utf-8") as handle:
                saved = json.load(handle)
            keys = [str(key) for key in saved if str(key).strip()]
            if keys:
                return keys[:tags.MAX_RECENT_KEYS]
        except (OSError, ValueError, TypeError):
            pass
        return list(tags.DEFAULT_RECENT_KEYS)

    def make_arrow_image(self, color):
        # Qt ignores width/height on ::down-arrow, so a CSS border triangle
        # renders as a rectangle. A real image is the only reliable arrow.
        try:
            folder = os.path.dirname(self.recent_keys_path())
            path = os.path.join(folder, f"arrow_{color.lstrip('#')}.png")
            pixmap = QPixmap(14, 9)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawPolygon(
                QPolygon([QPoint(1, 2), QPoint(13, 2), QPoint(7, 8)])
            )
            painter.end()
            if pixmap.save(path, "PNG"):
                return path.replace("\\", "/")
        except OSError as error:
            self.logger.warning(f"Could not draw the dropdown arrow: {error}")
        return ""

    def save_recent_keys(self):
        try:
            with open(self.recent_keys_path(), "w", encoding="utf-8") as handle:
                json.dump(self.recent_keys, handle, indent=2)
        except OSError as error:
            self.logger.warning(f"Could not save recent keys: {error}")

    def open_logs_folder(self):
        if sys.platform == 'win32':
            os.startfile(self.log_dir)
        elif sys.platform == 'darwin':
            subprocess.run(['open', self.log_dir])
        else:
            subprocess.run(['xdg-open', self.log_dir])

    def init_ui(self):
        self.apply_stylesheet()
        self.build_layout()

    def apply_stylesheet(self):
        style = """
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
            QComboBox {
                max-height: 30px;
            }
            QComboBox::drop-down {
                border: none;
                width: 22px;
            }
            QComboBox::down-arrow {
                __ARROW_IMAGE__
                margin-right: 8px;
            }
            QComboBox::down-arrow:hover {
                __ARROW_HOVER__
            }
            QComboBox QAbstractItemView {
                background-color: #181825;
                color: #cdd6f4;
                selection-background-color: #45475a;
                max-height: 150px;
                min-height: 30px;
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
            QPushButton#tagBtn {
                background-color: #cba6f7;
                color: #1e1e2e;
                padding: 6px 12px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                border-radius: 8px;
            }
            QPushButton#tagBtn:hover {
                background-color: #ddb6fc;
            }
            QPushButton#keyChip {
                background-color: #313244;
                color: #cdd6f4;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: normal;
                border-radius: 8px;
            }
            QPushButton#keyChip:hover {
                background-color: #45475a;
                color: #89b4fa;
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
        """

        arrow = self.make_arrow_image("#cdd6f4")
        arrow_hover = self.make_arrow_image("#89b4fa")
        fallback = (
            "image: none;"
            "border-left: 5px solid transparent;"
            "border-right: 5px solid transparent;"
            "border-top: 6px solid %s;"
        )
        style = style.replace(
            "__ARROW_IMAGE__",
            f"image: url({arrow});" if arrow else fallback % "#cdd6f4",
        )
        style = style.replace(
            "__ARROW_HOVER__",
            f"image: url({arrow_hover});" if arrow_hover else fallback % "#89b4fa",
        )
        self.setStyleSheet(style)

    def build_layout(self):
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
        self.text_edit.setPlaceholderText(
            "Paste your code here...\n\n"
            "Tags:  <KeyPress> Ctrl + C <KeyPress>    <Wait> 120 <Wait>\n"
            "A space starts the next press:  <KeyPress> Right Right Right <KeyPress>\n"
            "A tag-only line types no newline - use <KeyPress> Enter <KeyPress>"
        )
        text_layout.addWidget(self.text_edit)
        main.addWidget(text_group)

        tag_group = QGroupBox("Quick Insert")
        tag_layout = QHBoxLayout(tag_group)
        tag_layout.setSpacing(8)

        keypress_btn = QPushButton("<KeyPress>")
        keypress_btn.setObjectName("tagBtn")
        keypress_btn.setCursor(Qt.PointingHandCursor)
        keypress_btn.setToolTip(
            "Insert an empty KeyPress tag (Ctrl+K)\n"
            "'+' joins a combo, a space starts the next press"
        )
        keypress_btn.clicked.connect(self.insert_keypress_tag)
        tag_layout.addWidget(keypress_btn)

        wait_btn = QPushButton("<Wait>")
        wait_btn.setObjectName("tagBtn")
        wait_btn.setCursor(Qt.PointingHandCursor)
        wait_btn.setToolTip("Insert an empty Wait tag (Ctrl+Shift+W)")
        wait_btn.clicked.connect(self.insert_wait_tag)
        tag_layout.addWidget(wait_btn)

        recent_label = QLabel("Recent:")
        recent_label.setStyleSheet("color: #9399b2; font-size: 12px;")
        tag_layout.addWidget(recent_label)

        self.recent_container = QWidget()
        self.recent_layout = QHBoxLayout(self.recent_container)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setSpacing(6)
        tag_layout.addWidget(self.recent_container)

        tag_layout.addStretch()

        self.key_picker = QComboBox()
        self.key_picker.addItem("All keys...")
        self.key_picker.addItems(tags.PICKER_KEYS)
        self.key_picker.setMaxVisibleItems(12)
        self.key_picker.setToolTip("Pick any key or combo to insert as a tag")
        self.key_picker.activated.connect(self.on_key_picked)
        tag_layout.addWidget(self.key_picker)

        main.addWidget(tag_group)
        self.refresh_recent_keys()

        QShortcut(QKeySequence("Ctrl+K"), self, self.insert_keypress_tag)
        QShortcut(QKeySequence("Ctrl+Shift+W"), self, self.insert_wait_tag)

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
        self.lang_combo.setCurrentText("Plain Text")
        self.lang_combo.currentTextChanged.connect(self.on_language_changed)
        
        # Ensure dropdown has scrollbar and limited height
        self.lang_combo.setMaxVisibleItems(6)
        
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

    def refresh_recent_keys(self):
        while self.recent_layout.count():
            widget = self.recent_layout.takeAt(0).widget()
            if widget is not None:
                widget.deleteLater()

        for label in self.recent_keys[:8]:
            chip = QPushButton(label)
            chip.setObjectName("keyChip")
            chip.setCursor(Qt.PointingHandCursor)
            chip.setToolTip(f"Insert {tags.keypress_tag(label)}")
            chip.clicked.connect(
                lambda _checked=False, key=label: self.insert_key_tag(key)
            )
            self.recent_layout.addWidget(chip)

    def insert_snippet(self, snippet, caret_offset):
        cursor = self.text_edit.textCursor()
        start = cursor.selectionStart()
        cursor.insertText(snippet)
        cursor.setPosition(start + caret_offset)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.setFocus()

    def insert_keypress_tag(self):
        self.insert_snippet(tags.KEYPRESS_SNIPPET, tags.KEYPRESS_CARET)

    def insert_wait_tag(self):
        self.insert_snippet(tags.WAIT_SNIPPET, tags.WAIT_CARET)

    def insert_key_tag(self, label):
        tag = tags.keypress_tag(label)
        self.insert_snippet(tag, len(tag))
        self.on_keys_used(label)

    def on_key_picked(self, index):
        if index <= 0:
            return
        self.insert_key_tag(self.key_picker.itemText(index))
        self.key_picker.setCurrentIndex(0)

    def on_keys_used(self, label):
        if label in self.recent_keys:
            self.recent_keys.remove(label)
        self.recent_keys.insert(0, label)
        del self.recent_keys[tags.MAX_RECENT_KEYS:]
        self.refresh_recent_keys()
        self.save_recent_keys()

    def on_language_changed(self, lang):
        self.indent_size = self.LANG_INDENT.get(lang, 4)
        
        # For Plain Text, automatically uncheck auto-closing and auto-indentation
        if lang == "Plain Text":
            self.handle_autoclose.setChecked(False)
            self.handle_autoclose.setEnabled(False)
            self.handle_indent.setChecked(False)
            self.handle_indent.setEnabled(False)
            self.indent_info_label.setText("(plain text)")
            self.indent_info_label.setStyleSheet("color: #f38ba8; font-weight: bold;")
        else:
            # Re-enable the checkboxes when switching from Plain Text
            self.handle_autoclose.setEnabled(True)
            self.handle_indent.setEnabled(True)
            self.indent_info_label.setStyleSheet("color: #a6e3a1; font-weight: bold;")
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

    def update_status(self, msg):
        self.status_label.setText(f"Status: {msg}")
        self.status_label.setStyleSheet(
            "color: #fab387;" if "Waiting" in msg else "color: #9399b2;"
        )

    def start_typing(self):
        if not self.text_edit.toPlainText().strip():
            self.status_label.setText("Status: Please enter some text!")
            return

        problems = tags.validate(self.text_edit.toPlainText())
        if problems:
            self.status_label.setText(f"Status: {problems[0]}")
            for problem in problems:
                self.logger.warning(f"Tag problem: {problem}")
            return

        self.stop_flag = False
        self.current_line = 0
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Status: Starting...")
        self.status_label.setStyleSheet("color: #9399b2;")
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
        language = self.lang_combo.currentText()
        self.use_tabs = False

        self._type_text(
            text,
            line_delay,
            handle_autoclose,
            handle_indent,
            shift_enter,
            language,
        )

        self.signals.typing_finished.emit()

    def _type_text(
        self,
        text,
        line_delay,
        handle_autoclose,
        handle_indent,
        shift_enter=False,
        language=None,
    ):
        if language == "Plain Text" or (not handle_autoclose and not handle_indent):
            plain_text_sol.type_text(self, text, line_delay, shift_enter)
            return

        if language == "Python":
            python_sol.type_text(
                self,
                text,
                line_delay,
                handle_autoclose,
                handle_indent,
                shift_enter,
            )
            return

        char_interval = self.speed_slider.value() / 1000.0
        lines = text.splitlines()

        pending_closes = []
        current_indent_str = ""
        # Tag-only lines eat the newline around them, so several script lines
        # can land on one editor line. VS Code auto-indents from that whole
        # line, not from the last script line that fed it.
        editor_line = None
        editor_indent = ""

        for line_idx, line in enumerate(lines):
            if self.stop_flag:
                return

            self.report_line(line_idx + 1)
            original_indent = self._get_indentation(line)
            segments = tags.parse_line(line)

            # A line holding nothing but tags is the action itself, so it gets no
            # newline and takes no part in the indentation bookkeeping.
            if tags.line_is_tags_only(segments):
                tags.type_segments(
                    self,
                    tags.actions_only(segments),
                    char_interval,
                    False,
                    pending_closes,
                )
                continue

            if editor_line is None:
                editor_line = ""
                editor_indent = original_indent

            # Only strip the leading whitespace when _adjust_indentation is the
            # one writing it. With indentation handling off this must stay a
            # verbatim passthrough: every character, indentation included.
            if handle_indent:
                tags.strip_leading_indent(segments)

            tags.type_segments(
                self, segments, char_interval, handle_autoclose, pending_closes
            )
            editor_line += line

            if tags.types_newline(lines, line_idx):
                if shift_enter:
                    pyautogui.hotkey('shift', 'enter')
                    self.log(f"Line {line_idx+1}: pressed Shift+Enter")
                else:
                    pyautogui.press('enter')
                    self.log(f"Line {line_idx+1}: pressed Enter")

                next_index = tags.next_typed_index(lines, line_idx + 1)

                if handle_indent and next_index is not None:
                    time.sleep(0.2)  # Give VS Code time to auto‑indent
                    next_indent = self._get_indentation(lines[next_index])

                    last_non_space = editor_line.rstrip(' \t')
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
                    current_indent_str = editor_indent

                editor_line = None

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
        self.status_label.setStyleSheet("color: #9399b2;")
        self.log("Typing session ended")


if __name__ == "__main__":
    pyautogui.PAUSE = 0.01
    app = QApplication(sys.argv)
    window = AutoTyper()
    window.show()
    sys.exit(app.exec_())