import time

import pyautogui


def type_text(text, char_interval, line_delay, stop_checker, shift_enter=False):
    for character in text:
        if stop_checker():
            return

        if character == "\n":
            if shift_enter:
                pyautogui.hotkey("shift", "enter")
            else:
                pyautogui.hotkey("ctrl", "enter")
            if line_delay > 0:
                time.sleep(line_delay)
        elif character != "\r":
            pyautogui.write(character)
            time.sleep(char_interval)
