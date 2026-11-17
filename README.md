# Auto Typer

A simple GUI-based auto typer built with Python. Useful for typing code, commands, or repetitive text with configurable delay and speed.

**Small side project** — Nothing fancy, just a handy utility.

---

## Features

- Clean and modern dark-themed interface
- Large text area that preserves formatting (newlines, tabs, spaces, special characters)
- Adjustable delay before typing starts (with countdown)
- Typing speed control
- Key presses and hotkeys mid-script with `<KeyPress>` tags
- Per-line waits with `<Wait>` tags, on top of the global line delay
- Quick Insert tray with your recently used key presses
- Live status showing the line being typed and any wait counting down
- Start / Stop buttons
- PyAutoGUI failsafe support

---

## Tags

Tags let a script press keys and pause, instead of only typing characters. The
closing tag is the same as the opening one.

| Tag | Does |
| --- | --- |
| `<KeyPress> Enter <KeyPress>` | Presses a single key |
| `<KeyPress> Win + C <KeyPress>` | Presses a hotkey combination |
| `<KeyPress> Right Right Right <KeyPress>` | Presses Right three times |
| `<KeyPress> Ctrl + A Ctrl + C <KeyPress>` | Presses two combinations in order |
| `<Wait> 120 <Wait>` | Waits 120 seconds before carrying on |
| `<KeyPress> Up <KeyPress> <Wait> 5 <Wait>` | Several tags on one line, run in order |

Example:

```
winget install Python
<KeyPress> Enter <KeyPress>
<Wait> 120 <Wait>
python --version
<KeyPress> Enter <KeyPress>
```

Each command is run by an explicit `Enter` tag, the install is given two
minutes, and no stray newline is typed for the tag lines themselves.

### How tags behave

- A line that holds **only tags** is the action itself, not content, so **no
  newline is typed around it** — neither for the line break above it nor for its
  own. The text either side of such a line lands on the same line, which is what
  makes caret moves like `<KeyPress> Left Left <KeyPress>` land where you want.
  Press Enter yourself, with `<KeyPress> Enter <KeyPress>`, wherever a tag-only
  line should also break the line.
- An **empty line is always a newline**, tags below it or not: a newline is all
  an empty line is, so it keeps the one it stands for. Blank lines around a tag
  block therefore land in the target exactly as they sit in the script.
- A tag used **inside** a line runs in place, so
  `git branch <KeyPress> Enter <KeyPress>` types the command and then runs it.
- **Several tags can share one line** and run left to right, mixing both kinds:
  `<KeyPress> Right <KeyPress> <KeyPress> Up <KeyPress> <Wait> 5 <Wait> <KeyPress> Enter <KeyPress>`.
  On a line that holds only tags, the spaces between them are layout and are not
  typed into the target.
- Every key press is followed by a fixed **500 ms** pause, so the target has
  time to act on one key before the next arrives. It applies to each press in a
  sequence as well, and is not configurable.
- The global **Line Delay** still applies to every typed line. A `<Wait>` tag is
  extra, for the one spot that needs longer.
- The status bar names the line being typed, and counts a wait down live, as in
  `Status: Executing line 9... Waiting for 20 seconds...`.
- **Stop** interrupts a long wait straight away.
- A malformed tag stops the run before any typing starts, and the problem is
  shown in the status bar.
- Tags are not matched across lines; keep each one on a single line.

### Key names

Inside a `<KeyPress>` tag, `+` joins keys into one combination and **a space
starts the next press**. So `Ctrl + S` is one hotkey, while `Right Right Right`
is three presses of Right and `Ctrl + A Ctrl + C` is two hotkeys in order. Key
names that read as two words, such as `Page Up`, still count as one key.

Modifiers are `Ctrl`, `Alt`, `Shift` and `Win`, joined with `+`. Named keys
include `Enter`, `Tab`, `Esc`, `Space`, `Backspace`, `Delete`, `Insert`, `Home`,
`End`, `PageUp`, `PageDown`, the arrow keys `Up` / `Down` / `Left` / `Right`,
and `F1` to `F24`. Any single character works as itself, as in `Ctrl + C`.

`<Wait>` takes seconds by default and also accepts a unit, such as
`<Wait> 500ms <Wait>` or `<Wait> 2m <Wait>`.

### Quick Insert

The **Quick Insert** row under the text area writes the syntax for you:

- `<KeyPress>` and `<Wait>` insert an empty tag with the cursor already in the
  middle, ready for the key name or the number. Shortcuts are **Ctrl+K** and
  **Ctrl+Shift+W**.
- The **Recent** chips insert a complete tag for a key you have used before,
  most recent first. They are remembered between runs.
- **All keys...** lists the common keys and combinations to insert.

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

## Building

`build.bat` builds the application folder and then the installer. Pass the
version as the first argument:

```bat
build.bat 2.3.0
```

The build needs [Inno Setup 6](https://jrsoftware.org/isdl.php) for the
installer step. Without it the script still produces `dist\Auto Typer` and tells
you the installer was skipped.

Output:

- `installer_output\Auto-Typer-Setup-v<version>.exe` — the installer
- `dist\Auto Typer\` — the unpacked application folder

The installer is per-user, so it does not prompt for admin rights. It installs a
Start Menu entry, an optional desktop shortcut, and an uninstaller.

## Releases

Releases are driven entirely by git tags. Nothing is built on a push or a pull
request: the pipeline runs only when a version tag is pushed, and the version it
ships is the one in the tag.

1. Bump `VERSION` in `Typer.py` to the new number and commit it. The workflow
   fails the build if this does not match the tag, so the title bar and the
   installer can never disagree with the release.
2. Tag that commit and push the tag:

```bash
git tag -a v2.3.0 -m "Release v2.3.0"
git push origin v2.3.0
```

The tag must be `vMAJOR.MINOR.PATCH`; anything else is rejected before the build
starts. GitHub Actions then builds the onedir bundle, compiles the installer at
that version, and publishes the GitHub release with
`Auto-Typer-Setup-v<version>.exe` attached.

To redo a release, move the tag and force-push it:

```bash
git tag -f -a v2.3.0 -m "Release v2.3.0"
git push --force origin v2.3.0
```