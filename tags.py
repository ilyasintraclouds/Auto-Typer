import re
import time

import pyautogui


# <Tag> body <Tag> is the documented form; </Tag> is accepted as the closer too.
TAG_PATTERN = re.compile(
    r"<\s*(KeyPress|Wait)\s*>(.*?)<\s*/?\s*\1\s*>",
    re.IGNORECASE,
)
LOOSE_TAG_PATTERN = re.compile(r"<\s*/?\s*(KeyPress|Wait)\s*>", re.IGNORECASE)
# A "+" of its own joins keys; anything else is one key token.
KEY_TOKEN_PATTERN = re.compile(r"\+|[^\s+]+")

# Hardcoded breathing room after every key press. Apps and editors need a
# moment to act on a key before the next one lands, and a bare sequence of
# presses is useless if the target has not caught up.
KEYPRESS_DELAY = 0.5

KEYPRESS_SNIPPET = "<KeyPress>  <KeyPress>"
KEYPRESS_CARET = len("<KeyPress> ")
WAIT_SNIPPET = "<Wait>  <Wait>"
WAIT_CARET = len("<Wait> ")

DEFAULT_RECENT_KEYS = [
    "Enter",
    "Tab",
    "Esc",
    "Ctrl + C",
    "Ctrl + V",
    "Ctrl + S",
    "Win + R",
]
MAX_RECENT_KEYS = 10

MODIFIER_KEYS = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "altgr": "altright",
    "shift": "shift",
    "win": "win",
    "windows": "win",
    "super": "win",
    "meta": "win",
    "cmd": "win",
    "command": "win",
}

NAMED_KEYS = {
    "enter": "enter",
    "return": "enter",
    "tab": "tab",
    "esc": "esc",
    "escape": "esc",
    "space": "space",
    "spacebar": "space",
    "backspace": "backspace",
    "bksp": "backspace",
    "delete": "delete",
    "del": "delete",
    "insert": "insert",
    "ins": "insert",
    "home": "home",
    "end": "end",
    "pageup": "pageup",
    "pgup": "pageup",
    "pagedown": "pagedown",
    "pgdn": "pagedown",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "capslock": "capslock",
    "numlock": "numlock",
    "scrolllock": "scrolllock",
    "printscreen": "printscreen",
    "prtsc": "printscreen",
    "pause": "pause",
    "apps": "apps",
    "menu": "apps",
    "plus": "+",
    "minus": "-",
    "equals": "=",
    "comma": ",",
    "period": ".",
    "dot": ".",
    "slash": "/",
    "backslash": "\\",
    "semicolon": ";",
    "quote": "'",
}
NAMED_KEYS.update({f"f{number}": f"f{number}" for number in range(1, 25)})

DISPLAY_NAMES = {
    "ctrl": "Ctrl",
    "alt": "Alt",
    "altright": "AltGr",
    "shift": "Shift",
    "win": "Win",
    "enter": "Enter",
    "tab": "Tab",
    "esc": "Esc",
    "space": "Space",
    "backspace": "Backspace",
    "delete": "Delete",
    "insert": "Insert",
    "home": "Home",
    "end": "End",
    "pageup": "PageUp",
    "pagedown": "PageDown",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "capslock": "CapsLock",
    "numlock": "NumLock",
    "scrolllock": "ScrollLock",
    "printscreen": "PrintScreen",
    "pause": "Pause",
    "apps": "Menu",
}
DISPLAY_NAMES.update({f"f{number}": f"F{number}" for number in range(1, 25)})

# Longest-first so "ms" wins over "s" and "minutes" over "min".
WAIT_UNITS = (
    ("milliseconds", 0.001),
    ("millisecond", 0.001),
    ("ms", 0.001),
    ("minutes", 60.0),
    ("minute", 60.0),
    ("mins", 60.0),
    ("min", 60.0),
    ("m", 60.0),
    ("seconds", 1.0),
    ("second", 1.0),
    ("secs", 1.0),
    ("sec", 1.0),
    ("s", 1.0),
)

PICKER_KEYS = (
    "Enter",
    "Tab",
    "Esc",
    "Space",
    "Backspace",
    "Delete",
    "Up",
    "Down",
    "Left",
    "Right",
    "Home",
    "End",
    "PageUp",
    "PageDown",
    "F1",
    "F2",
    "F3",
    "F5",
    "F11",
    "F12",
    "Ctrl + C",
    "Ctrl + V",
    "Ctrl + X",
    "Ctrl + Z",
    "Ctrl + Y",
    "Ctrl + A",
    "Ctrl + S",
    "Ctrl + F",
    "Ctrl + P",
    "Ctrl + Enter",
    "Ctrl + Shift + P",
    "Ctrl + Shift + Enter",
    "Alt + Tab",
    "Alt + F4",
    "Shift + Enter",
    "Win + R",
    "Win + D",
    "Win + E",
    "Win + C",
)


def keypress_tag(label):
    return f"<KeyPress> {label} <KeyPress>"


def wait_tag(seconds):
    return f"<Wait> {seconds} <Wait>"


def has_tags(text):
    return TAG_PATTERN.search(text) is not None


def resolve_named(token):
    name = token.lower().replace(" ", "").replace("_", "").replace("-", "")
    if name in MODIFIER_KEYS:
        return MODIFIER_KEYS[name]
    return NAMED_KEYS.get(name)


def resolve_key(token):
    token = token.strip()
    key = resolve_named(token)
    if key is not None:
        return key
    if len(token) == 1:
        return token.lower()
    return None


def format_combo(keys):
    return " + ".join(
        DISPLAY_NAMES.get(key, key.upper() if len(key) == 1 else key.title())
        for key in keys
    )


def format_keys(combos):
    return " ".join(format_combo(keys) for keys in combos)


def parse_keys(body):
    # Whitespace separates one press from the next, "+" joins keys into a
    # single combination: "Right Right Right" is three presses, "Ctrl + S" one.
    tokens = KEY_TOKEN_PATTERN.findall(body)
    if not tokens:
        return None, "empty <KeyPress> tag"

    combos = []
    join = False
    index = 0

    while index < len(tokens):
        token = tokens[index]
        if token == "+":
            if not combos or join:
                return None, "stray '+' in <KeyPress> tag"
            join = True
            index += 1
            continue

        key = None
        # Key names spelled as two words ("Page Up", "Caps Lock") must not be
        # read as two separate presses, so a pair that names a key wins.
        if index + 1 < len(tokens) and tokens[index + 1] != "+":
            key = resolve_named(token + tokens[index + 1])
            if key is not None:
                index += 1
        if key is None:
            key = resolve_key(token)
        if key is None:
            return None, f"unknown key '{token}'"

        if join:
            combos[-1].append(key)
            join = False
        else:
            combos.append([key])
        index += 1

    if join:
        return None, "trailing '+' in <KeyPress> tag"
    return combos, None


def parse_wait(body):
    value = body.strip().lower().replace(" ", "")
    multiplier = 1.0
    for suffix, factor in WAIT_UNITS:
        if value.endswith(suffix):
            value = value[: -len(suffix)]
            multiplier = factor
            break

    try:
        seconds = float(value)
    except ValueError:
        return None, f"invalid <Wait> value '{body.strip()}'"
    if seconds < 0:
        return None, f"negative <Wait> value '{body.strip()}'"
    return seconds * multiplier, None


def parse_line(line):
    segments = []
    position = 0

    for match in TAG_PATTERN.finditer(line):
        if match.start() > position:
            segments.append(("text", line[position:match.start()]))

        body = match.group(2)
        if match.group(1).lower() == "keypress":
            keys, error = parse_keys(body)
            segments.append(("error", error) if error else ("key", keys))
        else:
            seconds, error = parse_wait(body)
            segments.append(("error", error) if error else ("wait", seconds))
        position = match.end()

    if position < len(line):
        segments.append(("text", line[position:]))
    return segments


def actions_only(segments):
    # The whitespace that separates tags on a tag-only line is layout, not
    # content, so it must not be typed into the target.
    return [segment for segment in segments if segment[0] != "text"]


def line_is_tags_only(segments):
    has_action = any(kind != "text" for kind, _ in segments)
    blank_text = all(
        value.strip() == "" for kind, value in segments if kind == "text"
    )
    return has_action and blank_text


def types_newline(lines, index):
    # The newline that puts a tag on its own line is syntax, not content, so the
    # line above a tag-only line does not end with a newline of its own. An
    # empty line is the exception: a newline is all it is, so it always keeps it.
    if index + 1 >= len(lines):
        return False
    if lines[index].strip() == "":
        return True
    return not line_is_tags_only(parse_line(lines[index + 1]))


def next_typed_index(lines, start):
    # Indentation lookahead must skip tag-only lines: they type nothing, so
    # their (absent) indentation is not what the next real line should match.
    for index in range(start, len(lines)):
        if not line_is_tags_only(parse_line(lines[index])):
            return index
    return None


def strip_leading_indent(segments):
    # Only the first text segment can carry the line's own indentation.
    if segments and segments[0][0] == "text":
        segments[0] = ("text", segments[0][1].lstrip(" \t"))
    return segments


def validate(text):
    problems = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for kind, value in parse_line(line):
            if kind == "error":
                problems.append(f"Line {line_number}: {value}")
        if LOOSE_TAG_PATTERN.search(TAG_PATTERN.sub("", line)):
            problems.append(f"Line {line_number}: unclosed tag")
    return problems


def rest(typer, seconds):
    # Ticks so Stop is noticed inside a delay instead of after it.
    deadline = time.monotonic() + seconds
    while not typer.stop_flag:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(0.05, remaining))


def press(typer, combos):
    label = format_keys(combos)
    typer.log(f"  KeyPress {label}")
    typer.report(f"Pressing {label}")
    for keys in combos:
        if typer.stop_flag:
            return
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)
        rest(typer, KEYPRESS_DELAY)
    typer.remember_keys(label)


def hold(typer, seconds):
    typer.log(f"  Wait {seconds}s")
    deadline = time.monotonic() + seconds
    shown = None

    # Ticks in place rather than sleeping the whole span, so the countdown
    # stays live and Stop is noticed within a fraction of a second.
    while not typer.stop_flag:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        countdown = int(remaining) + 1
        if countdown != shown:
            typer.report_wait(countdown)
            shown = countdown
        time.sleep(min(0.2, remaining))

    typer.report_line(typer.current_line)


def execute(typer, segment):
    kind, value = segment
    if kind == "key":
        press(typer, value)
    elif kind == "wait":
        hold(typer, value)
    elif kind == "error":
        typer.log(f"  Skipped tag: {value}")
        typer.report(f"Skipped tag: {value}")


def type_segments(typer, segments, char_interval, handle_autoclose, pending_closes):
    for segment in segments:
        if typer.stop_flag:
            return
        kind, value = segment

        if kind != "text":
            execute(typer, segment)
        elif not value:
            continue
        elif handle_autoclose:
            typer._type_content_with_autoclose(value, char_interval, pending_closes)
        else:
            for character in value:
                if typer.stop_flag:
                    return
                pyautogui.write(character)
                time.sleep(char_interval)
