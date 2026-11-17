import time

import pyautogui

import tags


DEDENT_STATEMENTS = ("break", "continue", "raise", "return")


def type_text(typer, text, line_delay, handle_autoclose, handle_indent, shift_enter=False):
    char_interval = typer.speed_slider.value() / 1000.0
    lines = text.splitlines()
    pending_closes = []
    current_indent_str = ""
    # Tag-only lines eat the newline around them, so several script lines can
    # land on one editor line. The editor auto-indents from that whole line.
    editor_line = None
    editor_indent = ""

    for line_idx, line in enumerate(lines):
        if typer.stop_flag:
            return

        typer.report_line(line_idx + 1)
        original_indent = typer._get_indentation(line)
        segments = tags.parse_line(line)

        # A line holding nothing but tags is the action itself, so it gets no
        # newline and takes no part in the indentation bookkeeping.
        if tags.line_is_tags_only(segments):
            tags.type_segments(
                typer,
                tags.actions_only(segments),
                char_interval,
                False,
                pending_closes,
            )
            continue

        if editor_line is None:
            editor_line = ""
            editor_indent = original_indent

        if handle_indent:
            tags.strip_leading_indent(segments)

        tags.type_segments(
            typer, segments, char_interval, handle_autoclose, pending_closes
        )
        editor_line += line

        if tags.types_newline(lines, line_idx):
            if shift_enter:
                pyautogui.hotkey("shift", "enter")
                typer.log(f"Line {line_idx + 1}: pressed Shift+Enter")
            else:
                pyautogui.press("enter")
                typer.log(f"Line {line_idx + 1}: pressed Enter")

            next_index = tags.next_typed_index(lines, line_idx + 1)

            if handle_indent and next_index is not None:
                time.sleep(0.2)
                next_indent = typer._get_indentation(lines[next_index])
                last_non_space = editor_line.rstrip(" \t")
                triggers_indent = (
                    last_non_space
                    and last_non_space[-1] in typer.AUTO_INDENT_CHARS
                )
                auto_indent = current_indent_str
                if triggers_indent:
                    auto_indent += " " * typer.indent_size
                    typer.log(
                        f"  Line ends with '{last_non_space[-1]}', "
                        "VS Code auto-indented"
                    )
                elif _dedents_after_statement(last_non_space):
                    auto_indent = auto_indent[:-typer.indent_size]
                    typer.log("  VS Code dedented after a control statement")

                typer.log(
                    f"  auto_indent = '{auto_indent}' (len={len(auto_indent)})"
                )
                typer.log(
                    f"  next_indent = '{next_indent}' (len={len(next_indent)})"
                )
                typer._adjust_indentation(
                    auto_indent, next_indent, char_interval
                )
                current_indent_str = next_indent
            else:
                current_indent_str = editor_indent

            editor_line = None

            if line_delay > 0:
                time.sleep(line_delay)


def _dedents_after_statement(line):
    statement = line.strip()
    return any(
        statement == keyword
        or statement.startswith(keyword + " ")
        or statement.startswith(keyword + "\t")
        or statement.startswith(keyword + "(")
        for keyword in DEDENT_STATEMENTS
    )
