import time

import pyautogui


DEDENT_STATEMENTS = ("break", "continue", "raise", "return")


def type_text(typer, text, line_delay, handle_autoclose, handle_indent, shift_enter=False):
    char_interval = typer.speed_slider.value() / 1000.0
    lines = text.splitlines()
    pending_closes = []
    current_indent_str = ""

    for line_idx, line in enumerate(lines):
        if typer.stop_flag:
            return

        original_indent = typer._get_indentation(line)
        content = line.lstrip(" \t") if handle_indent else line
        is_empty = content == ""

        if not is_empty:
            if handle_autoclose:
                typer._type_content_with_autoclose(content, char_interval, pending_closes)
            else:
                for character in content:
                    if typer.stop_flag:
                        return
                    pyautogui.write(character)
                    time.sleep(char_interval)

        if line_idx < len(lines) - 1:
            if shift_enter:
                pyautogui.hotkey("shift", "enter")
                typer.log(f"Line {line_idx + 1}: pressed Shift+Enter")
            else:
                pyautogui.press("enter")
                typer.log(f"Line {line_idx + 1}: pressed Enter")

            if handle_indent:
                time.sleep(0.2)
                next_indent = typer._get_indentation(lines[line_idx + 1])
                last_non_space = line.rstrip(" \t")
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
                current_indent_str = original_indent

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
