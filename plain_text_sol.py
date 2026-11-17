import time

import pyautogui

import tags


def type_text(typer, text, line_delay, shift_enter=False):
    char_interval = typer.speed_slider.value() / 1000.0
    lines = text.replace("\r", "").split("\n")

    for line_idx, line in enumerate(lines):
        if typer.stop_flag:
            return

        typer.report_line(line_idx + 1)
        segments = tags.parse_line(line)

        # A line holding nothing but tags is the action itself, so it gets no
        # newline, and the gaps between those tags are not typed either.
        if tags.line_is_tags_only(segments):
            tags.type_segments(
                typer, tags.actions_only(segments), char_interval, False, []
            )
            continue

        tags.type_segments(typer, segments, char_interval, False, [])

        if tags.types_newline(lines, line_idx):
            if shift_enter:
                pyautogui.hotkey("shift", "enter")
            else:
                pyautogui.hotkey("ctrl", "enter")
            if line_delay > 0:
                time.sleep(line_delay)
