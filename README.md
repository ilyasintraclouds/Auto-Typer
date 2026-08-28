# Auto Typer

A simple GUI-based auto typer built with Python. Useful for typing code, commands, or repetitive text with configurable delay and speed.

**Small side project** — Nothing fancy, just a handy utility.

---

## Features

- Clean and modern dark-themed interface
- Large text area that preserves formatting (newlines, tabs, spaces, special characters)
- Adjustable delay before typing starts (with countdown)
- Typing speed control
- Start / Stop buttons
- PyAutoGUI failsafe support

---

## Requirements

- Python 3.8 or higher

---

## Installation

1. Clone or download the project folder.
2. Open terminal/command prompt in the project directory.
3. Install the required packages:

```bash
pip install -r requirements.txt
```

## Execution
Use the following command to execute the script:
```bash
python Typer.py
```

## Releases

After committing the release changes, create and push a version tag:

```bash
git tag -a v2.2.0 -m "Release v2.2.0"
git push origin v2.2.0
```

GitHub Actions builds the executable and publishes the GitHub release for pushed `v*` tags.