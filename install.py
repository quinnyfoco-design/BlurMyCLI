#!/usr/bin/env python3

import curses
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
CONFIGS_DIR = REPO_DIR / "configs"
UTILS_DIR = REPO_DIR / "utils"
LOCAL_BIN = Path.home() / ".local" / "bin"
XDG_CONFIG = Path.home() / ".config"

DEPS = [
    ("hyprland",   "hyprctl",      None),
    ("kitty",      "kitty",        None),
    ("alacritty",  "alacritty",    None),
    ("fish",       "fish",         None),
    ("python3",    "python3",      None),
    ("hyprsunset", "hyprsunset",   None),
    ("hyprpaper",  "hyprpaper",    None),
    ("zen-browser","zen-browser",  None),
    ("dolphin",    "dolphin",      None),
    ("powerprofilesctl", "powerprofilesctl", None),
    ("htop",       "htop",         None),
    ("nmtui",      "nmtui",        None),
    ("vim",        "vim",          None),
    ("gsettings",  "gsettings",    None),
    ("cargo",      "cargo",        None),
    ("rapidfuzz",  None,           "python3 -c 'import rapidfuzz'"),
]

TITLE = "BlurMyCLI Installer"
VERSION = "v0.0.1"

THEME = {
    "accent": -1,
    "highlight": -1,
    "dim": -1,
    "success": -1,
    "error": -1,
    "border": -1,
}


def init_theme():
    if curses.has_colors():
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_MAGENTA, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_GREEN, -1)
        curses.init_pair(5, curses.COLOR_RED, -1)
        curses.init_pair(6, curses.COLOR_WHITE, -1)
        curses.init_pair(7, curses.COLOR_BLUE, -1)
        THEME["accent"] = curses.color_pair(1)
        THEME["highlight"] = curses.color_pair(2) | curses.A_BOLD
        THEME["dim"] = curses.A_DIM
        THEME["success"] = curses.color_pair(4)
        THEME["error"] = curses.color_pair(5)
        THEME["border"] = curses.color_pair(6) | curses.A_DIM


class InstallState:
    def __init__(self):
        self.os_name = ""
        self.is_arch = False
        self.dep_results: list[tuple[str, bool]] = []
        self.blur = True
        self.rec_utils = True
        self.config_action = "bak"
        self.existing_dirs: list[str] = []
        self.kb_layout = "us"
        self.wallpaper_path = ""
        self.terminal_choice = "kitty"
        self.kb_mode = "my_binds"
        self.keep_animations = True
        self.confirmed = False


def detect_os(state: InstallState):
    try:
        content = Path("/etc/os-release").read_text()
        for line in content.splitlines():
            if line.startswith("ID="):
                state.os_name = line.split("=", 1)[1].strip().strip("\"'")
                break
    except Exception:
        state.os_name = "unknown"
    state.is_arch = state.os_name == "arch"


def check_deps(state: InstallState):
    for name, binary, check_cmd in DEPS:
        if binary:
            found = shutil.which(binary) is not None
        else:
            found = subprocess.call(
                check_cmd, shell=True, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            ) == 0
        state.dep_results.append((name, found))


def find_existing_configs(state: InstallState):
    checks = [
        ("hypr",    XDG_CONFIG / "hypr" / "hyprland.conf"),
        ("kitty",   XDG_CONFIG / "kitty" / "kitty.conf"),
        ("alacritty", XDG_CONFIG / "alacritty" / "alacritty.toml"),
        ("fish",    XDG_CONFIG / "fish" / "config.fish"),
        ("opencode", XDG_CONFIG / "opencode" / "opencode.jsonc"),
        ("opencode", XDG_CONFIG / "opencode" / "tui.json"),
    ]
    seen = set()
    for name, path in checks:
        if path.exists() and name not in seen:
            seen.add(name)
            state.existing_dirs.append(name)


def draw_box(stdscr, y, x, h, w, attr=None):
    if attr is None:
        attr = THEME["border"]
    if w < 4 or h < 2:
        return
    btm = y + h - 1
    right = x + w - 1
    try:
        stdscr.addstr(y, x, "\u256d", attr)
        stdscr.addstr(y, right, "\u256e", attr)
        stdscr.addstr(btm, x, "\u2570", attr)
        stdscr.addstr(btm, right, "\u256f", attr)
        for cx in range(x + 1, right):
            stdscr.addstr(y, cx, "\u2500", attr)
            stdscr.addstr(btm, cx, "\u2500", attr)
        for cy in range(y + 1, btm):
            stdscr.addstr(cy, x, "\u2502", attr)
            stdscr.addstr(cy, right, "\u2502", attr)
    except curses.error:
        pass


def draw_horiz(stdscr, y, x, w, attr=None):
    if attr is None:
        attr = THEME["border"]
    try:
        for cx in range(x, x + w):
            stdscr.addstr(y, cx, "\u2500", attr)
    except curses.error:
        pass


def draw_footer(stdscr, text):
    rows, cols = stdscr.getmaxyx()
    if cols < 6:
        return
    try:
        attr = THEME["dim"]
        stdscr.addstr(rows - 2, 2, "\u2570" + "\u2500" * (cols - 6) + "\u256f", attr)
    except curses.error:
        pass
    try:
        cx = (cols - len(text)) // 2
        if cx < 2:
            cx = 2
        stdscr.addstr(rows - 2, cx, f" {text} ", THEME["dim"])
    except curses.error:
        pass


def await_key(stdscr):
    while True:
        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            continue
        if key in (10, 13, 32, ord("q"), ord("Q"), 27):
            return


def screen_welcome(stdscr):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()
    if cols < 40:
        return False

    box_w = min(50, cols - 4)
    box_h = 9
    bx = (cols - box_w) // 2
    by = (rows - box_h) // 2 - 2

    draw_box(stdscr, by, bx, box_h, box_w)

    title = f" {TITLE} "
    ver = f" {VERSION} "
    sub = " a CLI-focused Hyprland dotfile setup "
    prompt = " Press SPACE / ENTER to begin "
    quit_ = " Press ESC / Q to quit "

    cx = (cols - len(title)) // 2
    stdscr.addstr(by + 1, cx, title, THEME["highlight"])
    cx = (cols - len(ver)) // 2
    stdscr.addstr(by + 2, cx, ver, THEME["accent"])
    cx = (cols - len(sub)) // 2
    stdscr.addstr(by + 4, cx, sub, THEME["dim"])
    cx = (cols - len(prompt)) // 2
    stdscr.addstr(by + 6, cx, prompt, THEME["success"])
    cx = (cols - len(quit_)) // 2
    stdscr.addstr(by + 7, cx, quit_, THEME["error"])

    curses.curs_set(0)
    stdscr.refresh()

    while True:
        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            return screen_welcome(stdscr)
        if key in (10, 13, 32):
            return True
        if key in (27, ord("q"), ord("Q")):
            return False


def screen_os_check(stdscr, state: InstallState):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    box_w = min(44, cols - 4)
    box_h = 6
    bx = (cols - box_w) // 2
    by = (rows - box_h) // 2

    draw_box(stdscr, by, bx, box_h, box_w)

    title = " OS Detection "
    cx = (cols - len(title)) // 2
    stdscr.addstr(by + 1, cx, title, THEME["highlight"])

    os_txt = f" Detected: {state.os_name} "
    cx = (cols - len(os_txt)) // 2
    stdscr.addstr(by + 3, cx, os_txt, THEME["accent"])

    if state.is_arch:
        msg = " Arch Linux detected "
        a = THEME["success"]
    else:
        msg = f" {state.os_name} may not be fully compatible "
        a = THEME["error"]
    cx = (cols - len(msg)) // 2
    stdscr.addstr(by + 4, cx, msg, a)

    draw_footer(stdscr, "SPACE / ENTER to continue")
    curses.curs_set(0)
    stdscr.refresh()
    await_key(stdscr)


def screen_kb_layout_prompt(stdscr, state: InstallState):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    box_w = min(46, cols - 4)
    box_h = 7
    bx = (cols - box_w) // 2
    by = (rows - box_h) // 2

    draw_box(stdscr, by, bx, box_h, box_w)

    title = " Keyboard Layout "
    cx = (cols - len(title)) // 2
    stdscr.addstr(by + 1, cx, title, THEME["highlight"])

    hint = " enter layout code (us, de, fr, gb, jp...) "
    cx = (cols - len(hint)) // 2
    stdscr.addstr(by + 3, cx, hint, THEME["dim"])

    path = state.kb_layout
    y = by + 5
    curses.curs_set(1)

    while True:
        stdscr.addstr(y, bx + 2, " " * (box_w - 4))
        display = f"> {path} "
        stdscr.addstr(y, bx + 2, display, THEME["accent"])
        stdscr.move(y, bx + 4 + len(path))
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            rows, cols = stdscr.getmaxyx()
            return screen_kb_layout_prompt(stdscr, state)
        if key in (10, 13):
            break
        elif key in (27, ord("q"), ord("Q")):
            curses.curs_set(0)
            return False
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            path = path[:-1]
        elif 32 <= key <= 126:
            if len(path) < 10:
                path += chr(key)

    trimmed = path.strip().lower()
    if trimmed:
        state.kb_layout = trimmed

    curses.curs_set(0)
    return True


def screen_dep_check(stdscr, state: InstallState):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    box_w = min(42, cols - 4)
    bx = (cols - box_w) // 2
    by = 2

    scroll = 0
    max_visible = rows - by - 5

    while True:
        stdscr.erase()
        rows, cols = stdscr.getmaxyx()
        box_w = min(42, cols - 4)
        bx = (cols - box_w) // 2
        max_visible = rows - by - 5

        draw_box(stdscr, by, bx, min(max_visible + 3, len(state.dep_results) + 3), box_w)

        title = " Dependency Check "
        cx = (cols - len(title)) // 2
        stdscr.addstr(by + 1, cx, title, THEME["highlight"])

        visible = state.dep_results[scroll:scroll + max_visible]
        for i, (name, found) in enumerate(visible):
            icon = "\u2713" if found else "\u2717"
            icon_attr = THEME["success"] if found else THEME["error"]
            label = f" {icon} {name} "
            stdscr.addstr(by + 3 + i, bx + 2, label, icon_attr)

        total = len(state.dep_results)
        if total > max_visible:
            pct = f" [{scroll + 1}-{min(scroll + max_visible, total)}/{total}] "
            stdscr.addstr(rows - 3, cols - len(pct) - 2, pct, THEME["dim"])

        draw_footer(stdscr, "\u2191\u2195 scroll  SPACE / ENTER to continue")
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            continue
        if key == curses.KEY_UP and scroll > 0:
            scroll -= 1
        elif key == curses.KEY_DOWN and scroll + max_visible < total:
            scroll += 1
        elif key in (10, 13, 32):
            break
        elif key in (27, ord("q"), ord("Q")):
            return False
    return True


def screen_blur_prompt(stdscr, state: InstallState):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    box_w = min(48, cols - 4)
    box_h = 8
    bx = (cols - box_w) // 2
    by = (rows - box_h) // 2

    draw_box(stdscr, by, bx, box_h, box_w)

    title = " Blur Configuration "
    cx = (cols - len(title)) // 2
    stdscr.addstr(by + 1, cx, title, THEME["highlight"])

    desc = " enable glass-like transparency? "
    cx = (cols - len(desc)) // 2
    stdscr.addstr(by + 3, cx, desc, THEME["dim"])

    choice = state.blur
    while True:
        y = by + 5
        yes_attr = THEME["success"] | curses.A_REVERSE if choice else THEME["success"]
        no_attr = THEME["error"] | curses.A_REVERSE if not choice else THEME["error"]
        stdscr.addstr(y, bx + 6, " [Y]  Yes  ", yes_attr)
        stdscr.addstr(y, bx + 20, " [N]  No  ", no_attr)
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            return screen_blur_prompt(stdscr, state)
        if key in (ord("y"), ord("Y")):
            choice = True
        elif key in (ord("n"), ord("N")):
            choice = False
        elif key == curses.KEY_LEFT:
            choice = True
        elif key == curses.KEY_RIGHT:
            choice = False
        elif key in (10, 13, 32):
            state.blur = choice
            break
        elif key in (27, ord("q"), ord("Q")):
            return False
    return True


def screen_rec_utils_prompt(stdscr, state: InstallState):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    box_w = min(52, cols - 4)
    box_h = 9
    bx = (cols - box_w) // 2
    by = (rows - box_h) // 2

    draw_box(stdscr, by, bx, box_h, box_w)

    title = " Recommended Utilities "
    cx = (cols - len(title)) // 2
    stdscr.addstr(by + 1, cx, title, THEME["highlight"])

    desc = " install CLI tools + eightfetch? "
    cx = (cols - len(desc)) // 2
    stdscr.addstr(by + 3, cx, desc, THEME["dim"])
    desc2 = " (cli-menu, cli-search, cli-launch) "
    cx = (cols - len(desc2)) // 2
    stdscr.addstr(by + 4, cx, desc2, THEME["dim"])

    choice = state.rec_utils
    while True:
        y = by + 6
        yes_attr = THEME["success"] | curses.A_REVERSE if choice else THEME["success"]
        no_attr = THEME["error"] | curses.A_REVERSE if not choice else THEME["error"]
        stdscr.addstr(y, bx + 6, " [Y]  Yes  ", yes_attr)
        stdscr.addstr(y, bx + 20, " [N]  No  ", no_attr)
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            return screen_rec_utils_prompt(stdscr, state)
        if key in (ord("y"), ord("Y")):
            choice = True
        elif key in (ord("n"), ord("N")):
            choice = False
        elif key == curses.KEY_LEFT:
            choice = True
        elif key == curses.KEY_RIGHT:
            choice = False
        elif key in (10, 13, 32):
            state.rec_utils = choice
            break
        elif key in (27, ord("q"), ord("Q")):
            return False
    return True


def screen_wallpaper_prompt(stdscr, state: InstallState):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    box_w = min(52, cols - 4)
    box_h = 8
    bx = (cols - box_w) // 2
    by = (rows - box_h) // 2

    draw_box(stdscr, by, bx, box_h, box_w)

    title = " Wallpaper Setup "
    cx = (cols - len(title)) // 2
    stdscr.addstr(by + 1, cx, title, THEME["highlight"])

    hint = " enter path to image, or leave empty "
    cx = (cols - len(hint)) // 2
    stdscr.addstr(by + 3, cx, hint, THEME["dim"])

    path = ""
    y = by + 5
    IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    curses.curs_set(1)

    while True:
        stdscr.addstr(y, bx + 2, " " * (box_w - 4))
        display = f"> {path} "
        stdscr.addstr(y, bx + 2, display, THEME["accent"])

        trimmed = path.strip()
        if trimmed:
            p = Path(trimmed).expanduser()
            if not p.exists():
                err = " file not found "
                stdscr.addstr(by + 6, bx + 2, err, THEME["error"])
            elif p.suffix.lower() not in IMAGE_EXTS:
                err = " unsupported format (png/jpg/webp/bmp) "
                stdscr.addstr(by + 6, bx + 2, err, THEME["error"])

        stdscr.move(y, bx + 4 + len(path))
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            curses.curs_set(0)
            return screen_wallpaper_prompt(stdscr, state)
        if key in (10, 13):
            break
        elif key in (27, ord("q"), ord("Q")):
            curses.curs_set(0)
            return False
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            path = path[:-1]
        elif 32 <= key <= 126:
            path += chr(key)

    trimmed = path.strip()
    if trimmed:
        p = Path(trimmed).expanduser()
        if p.exists() and p.suffix.lower() in IMAGE_EXTS:
            state.wallpaper_path = str(p.resolve())

    curses.curs_set(0)
    return True


def screen_terminal_prompt(stdscr, state: InstallState) -> bool:
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    box_w = min(56, cols - 4)
    box_h = 9
    bx = (cols - box_w) // 2
    by = (rows - box_h) // 2

    draw_box(stdscr, by, bx, box_h, box_w)

    title = " Terminal Emulator "
    cx = (cols - len(title)) // 2
    stdscr.addstr(by + 1, cx, title, THEME["highlight"])

    options = [
        ("kitty", "Kitty", "GPU-accelerated, feature-rich"),
        ("alacritty", "Alacritty", "GPU-accelerated, minimal"),
    ]
    choice_idx = 0 if state.terminal_choice == "kitty" else 1

    while True:
        y = by + 3
        for i, (val, label, desc) in enumerate(options):
            if i == choice_idx:
                attr = THEME["highlight"] | curses.A_REVERSE
                marker = "\u25b6 "
            else:
                attr = THEME["dim"]
                marker = "  "
            stdscr.addstr(y, bx + 4, f" {marker}{label} ", attr)
            stdscr.addstr(y, bx + 18, f" {desc} ", THEME["dim"])
            y += 1

        draw_footer(stdscr, "\u2191\u2195 select  SPACE / ENTER to confirm")
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            return screen_terminal_prompt(stdscr, state)
        if key == curses.KEY_UP and choice_idx > 0:
            choice_idx -= 1
        elif key == curses.KEY_DOWN and choice_idx < len(options) - 1:
            choice_idx += 1
        elif key in (10, 13, 32):
            state.terminal_choice = options[choice_idx][0]
            break
        elif key in (27, ord("q"), ord("Q")):
            return False
    return True


def screen_bindings_prompt(stdscr, state: InstallState) -> bool:
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    box_w = min(58, cols - 4)
    box_h = 10
    bx = (cols - box_w) // 2
    by = (rows - box_h) // 2

    draw_box(stdscr, by, bx, box_h, box_w)

    title = " Keybindings "
    cx = (cols - len(title)) // 2
    stdscr.addstr(by + 1, cx, title, THEME["highlight"])

    options = [
        ("my_binds", "My Binds", "Full set (SUPER+S, Q, M, arrows...)"),
        ("basic", "Basic Binds", "Essentials (kill, exit, menu, term)"),
    ]
    choice_idx = 0 if state.kb_mode == "my_binds" else 1

    while True:
        y = by + 3
        for i, (val, label, desc) in enumerate(options):
            if i == choice_idx:
                attr = THEME["highlight"] | curses.A_REVERSE
                marker = "\u25b6 "
            else:
                attr = THEME["dim"]
                marker = "  "
            stdscr.addstr(y, bx + 4, f" {marker}{label} ", attr)
            stdscr.addstr(y, bx + 20, f" {desc} ", THEME["dim"])
            y += 1

        draw_footer(stdscr, "\u2191\u2195 select  SPACE / ENTER to confirm")
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            return screen_bindings_prompt(stdscr, state)
        if key == curses.KEY_UP and choice_idx > 0:
            choice_idx -= 1
        elif key == curses.KEY_DOWN and choice_idx < len(options) - 1:
            choice_idx += 1
        elif key in (10, 13, 32):
            state.kb_mode = options[choice_idx][0]
            break
        elif key in (27, ord("q"), ord("Q")):
            return False
    return True


def screen_animations_prompt(stdscr, state: InstallState) -> bool:
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    box_w = min(56, cols - 4)
    box_h = 9
    bx = (cols - box_w) // 2
    by = (rows - box_h) // 2

    draw_box(stdscr, by, bx, box_h, box_w)

    title = " Animations "
    cx = (cols - len(title)) // 2
    stdscr.addstr(by + 1, cx, title, THEME["highlight"])

    desc = " keep animations from your current config? "
    cx = (cols - len(desc)) // 2
    stdscr.addstr(by + 3, cx, desc, THEME["dim"])
    desc2 = " (No = Hyprland defaults, clean & minimal) "
    cx = (cols - len(desc2)) // 2
    stdscr.addstr(by + 4, cx, desc2, THEME["dim"])

    choice = state.keep_animations
    while True:
        y = by + 6
        yes_attr = THEME["success"] | curses.A_REVERSE if choice else THEME["success"]
        no_attr = THEME["error"] | curses.A_REVERSE if not choice else THEME["error"]
        stdscr.addstr(y, bx + 6, " [Y]  Yes  ", yes_attr)
        stdscr.addstr(y, bx + 20, " [N]  No  ", no_attr)
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            return screen_animations_prompt(stdscr, state)
        if key in (ord("y"), ord("Y")):
            choice = True
        elif key in (ord("n"), ord("N")):
            choice = False
        elif key == curses.KEY_LEFT:
            choice = True
        elif key == curses.KEY_RIGHT:
            choice = False
        elif key in (10, 13, 32):
            state.keep_animations = choice
            break
        elif key in (27, ord("q"), ord("Q")):
            return False
    return True


def screen_existing_configs(stdscr, state: InstallState):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    by = 2
    box_w = min(50, cols - 4)

    if not state.existing_dirs:
        bx = (cols - min(44, box_w)) // 2
        box_h = 4
        draw_box(stdscr, by, bx, box_h, min(44, box_w))
        title = " Existing Configurations "
        cx = (cols - len(title)) // 2
        stdscr.addstr(by + 1, cx, title, THEME["highlight"])
        msg = " no existing configs found — fresh install! "
        cx = (cols - len(msg)) // 2
        stdscr.addstr(by + 2, cx, msg, THEME["success"])
        draw_footer(stdscr, "SPACE / ENTER to continue")
        stdscr.refresh()
        await_key(stdscr)
        return True

    options = [
        ("B", "Backup + Overwrite", "bak"),
        ("O", "Overwrite directly", "overwrite"),
        ("S", "Skip existing", "skip"),
    ]

    choice_idx = 0
    for i, (key, label, _) in enumerate(options):
        if state.config_action == options[i][2]:
            choice_idx = i
            break

    while True:
        stdscr.erase()
        rows, cols = stdscr.getmaxyx()
        box_w = min(50, cols - 4)
        content_h = 2 + len(state.existing_dirs) + 2 + len(options) + 1
        box_h = content_h + 2
        bx = (cols - box_w) // 2
        by = max(1, (rows - box_h) // 2)

        draw_box(stdscr, by, bx, box_h, box_w)

        title = " Existing Configurations "
        cx = (cols - len(title)) // 2
        stdscr.addstr(by + 1, cx, title, THEME["highlight"])

        y = by + 3
        for name in state.existing_dirs:
            line = f" found: ~/.config/{name}/ "
            stdscr.addstr(y, bx + 3, line, THEME["accent"])
            y += 1

        y += 1
        handler_txt = " how to handle existing files? "
        cx = (cols - len(handler_txt)) // 2
        stdscr.addstr(y, cx, handler_txt, THEME["dim"])
        y += 1

        for i, (key, label, _) in enumerate(options):
            if i == choice_idx:
                attr = THEME["highlight"] | curses.A_REVERSE
            else:
                attr = THEME["dim"]
            stdscr.addstr(y, bx + 6, f" [{key}]  {label} ", attr)
            y += 1

        draw_footer(stdscr, "\u2191\u2195 select  SPACE / ENTER to confirm")
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            continue
        if key == curses.KEY_UP and choice_idx > 0:
            choice_idx -= 1
        elif key == curses.KEY_DOWN and choice_idx < len(options) - 1:
            choice_idx += 1
        elif key in (10, 13, 32):
            state.config_action = options[choice_idx][2]
            break
        elif key in (27, ord("q"), ord("Q")):
            return False
    return True


def screen_summary(stdscr, state: InstallState):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    missing = [n for n, f in state.dep_results if not f]
    blur_text = "enabled" if state.blur else "disabled"
    rec_text = "yes" if state.rec_utils else "no"
    anim_text = "keep mine" if state.keep_animations else "defaults"
    action_labels = {"bak": "backup + overwrite", "overwrite": "overwrite", "skip": "skip"}
    config_text = action_labels.get(state.config_action, state.config_action)
    wall_text = state.wallpaper_path if state.wallpaper_path else "none"

    items = [
        ("OS", state.os_name),
        ("Keyboard", state.kb_layout),
        ("Missing", ', '.join(missing) if missing else 'none'),
        ("Blur", blur_text),
        ("Rec utils", rec_text),
        ("Terminal", state.terminal_choice),
        ("Bindings", 'My Binds' if state.kb_mode == 'my_binds' else 'Basic Binds'),
        ("Animations", anim_text),
        ("Wallpaper", wall_text),
        ("Existing", config_text),
    ]

    box_w = min(50, cols - 4)
    content_h = 3 + len(items) + 3
    box_h = content_h + 2
    bx = (cols - box_w) // 2
    by = max(1, (rows - box_h) // 2)

    draw_box(stdscr, by, bx, box_h, box_w)

    title = " Installation Summary "
    cx = (cols - len(title)) // 2
    stdscr.addstr(by + 1, cx, title, THEME["highlight"])

    y = by + 3
    for label, value in items:
        line = f" {label}: ".ljust(15)
        stdscr.addstr(y, bx + 3, line, THEME["dim"])
        stdscr.addstr(y, bx + 3 + 15, value, THEME["accent"])
        y += 1

    y += 1
    choice = True
    while True:
        yes_attr = THEME["success"] | curses.A_REVERSE if choice else THEME["success"]
        no_attr = THEME["error"] | curses.A_REVERSE if not choice else THEME["error"]
        stdscr.addstr(y, bx + 4, " [Y]  Yes, install!  ", yes_attr)
        stdscr.addstr(y, bx + 26, " [N]  No, cancel  ", no_attr)
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            return screen_summary(stdscr, state)
        if key in (ord("y"), ord("Y")):
            choice = True
        elif key in (ord("n"), ord("N")):
            choice = False
        elif key in (10, 13, 32):
            state.confirmed = choice
            break
        elif key in (27, ord("q"), ord("Q")):
            state.confirmed = False
            break

    if not state.confirmed:
        screen_cancelled(stdscr)
        return False
    return True


def screen_installing(stdscr, state: InstallState):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    box_w = min(50, cols - 4)
    bx = (cols - box_w) // 2
    by = 1

    log = []
    log_y = by + 2

    def log_msg(msg, ok=True):
        nonlocal log_y
        icon = "\u2713" if ok else "\u2717"
        icon_attr = THEME["success"] if ok else THEME["error"]
        label = f" {icon} {msg} "
        stdscr.addstr(log_y, bx + 2, label, icon_attr)
        log_y += 1
        stdscr.refresh()

    stdscr.erase()
    rows, cols = stdscr.getmaxyx()
    box_w = min(50, cols - 4)
    bx = (cols - box_w) // 2
    by = 1

    draw_box(stdscr, by, bx, 3, box_w)
    title = " Installing... "
    cx = (cols - len(title)) // 2
    stdscr.addstr(by + 1, cx, title, THEME["highlight"])
    stdscr.refresh()

    BASIC_BINDS = """# binds
bind = $mainMod, Q, killactive,
bind = $mainMod, C, exec, command -v hyprshutdown >/dev/null 2>&1 && hyprshutdown || hyprctl dispatch exit
bind = $mainMod, M, exec, __TERMINAL__ --class cli-menu --title cli-menu -e $menu
bind = $mainMod, S, exec, $terminal
bind = $mainMod, E, exec, $fileManager
bind = $mainMod, Space, exec, __TERMINAL__ --class cli-launch --title cli-launch -e $appLauncher
bind = $mainMod, V, togglefloating,
bindm = $mainMod, mouse:272, movewindow
bindm = $mainMod, mouse:273, resizewindow
bind = $mainMod, left, movefocus, l
bind = $mainMod, right, movefocus, r
bind = $mainMod, up, movefocus, u
bind = $mainMod, down, movefocus, d
bind = $mainMod SHIFT, left, movewindow, l
bind = $mainMod SHIFT, right, movewindow, r
bind = $mainMod SHIFT, up, movewindow, u
bind = $mainMod SHIFT, down, movewindow, d
"""

    try:
        existing_animations = ""
        if state.keep_animations:
            existing_hypr = XDG_CONFIG / "hypr" / "hyprland.conf"
            if existing_hypr.exists():
                existing_content = existing_hypr.read_text()
                anim_start = existing_content.find("# animation\n")
                if anim_start != -1:
                    deco_start = existing_content.find("\n# deco", anim_start)
                    if deco_start == -1:
                        deco_start = len(existing_content)
                    existing_animations = existing_content[anim_start:deco_start].strip()

        term_subdir = state.terminal_choice
        term_file = "kitty.conf" if state.terminal_choice == "kitty" else "alacritty.toml"
        config_mapping = [
            ("hypr",    "hyprland.conf"),
            (term_subdir, term_file),
            ("fish",    "config.fish"),
            ("opencode","opencode.jsonc"),
            ("opencode","tui.json"),
        ]

        if state.config_action != "skip":
            for subdir, filename in config_mapping:
                src = CONFIGS_DIR / subdir / filename
                dst_dir = XDG_CONFIG / subdir
                dst = dst_dir / filename

                if state.config_action == "bak" and dst.exists():
                    bak = dst.parent / f"{dst.name}.bak"
                    i = 1
                    while bak.exists():
                        bak = dst.parent / f"{dst.name}.bak.{i}"
                        i += 1
                    shutil.copy2(dst, bak)

                dst_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

            log_msg("Copied configs to ~/.config/")
        else:
            log_msg("Skipped config deployment", False)

        hypr_conf = XDG_CONFIG / "hypr" / "hyprland.conf"
        if hypr_conf.exists():
            content = hypr_conf.read_text()
            replacements = {
                "__CLI_LAUNCH_PATH__": f"{LOCAL_BIN}/cli-launch.py",
                "__CLI_SEARCH_PATH__": f"{LOCAL_BIN}/cli-search.py",
                "__CLI_MENU_PATH__":   f"{LOCAL_BIN}/cli-menu.py",
                "__KB_LAYOUT__":       state.kb_layout,
                "__TERMINAL__":        state.terminal_choice,
            }
            for old, new in replacements.items():
                content = content.replace(old, new)

            if state.kb_mode == "basic":
                binds_start = content.find("# binds\n")
                anim_start = content.find("\n# animation")
                if binds_start != -1 and anim_start != -1:
                    content = content[:binds_start] + BASIC_BINDS + content[anim_start:]

            if not state.blur:
                content = content.replace("enabled = true", "enabled = false")

            if state.wallpaper_path:
                if "exec-once = hyprpaper" not in content:
                    content = content.replace(
                        "exec-once = hyprsunset",
                        "exec-once = hyprpaper &\nexec-once = hyprsunset",
                    )

            hypr_conf.write_text(content)

            if state.keep_animations and existing_animations:
                hypr_content = hypr_conf.read_text()
                anim_start = hypr_content.find("# animation\n")
                deco_start = hypr_content.find("\n# deco")
                if anim_start != -1 and deco_start != -1:
                    hypr_content = hypr_content[:anim_start] + existing_animations + hypr_content[deco_start:]
                    hypr_conf.write_text(hypr_content)
                    log_msg("Injected your custom animations")
                else:
                    log_msg("Could not inject animations (section markers missing)", False)
            elif not state.keep_animations:
                hypr_content = hypr_conf.read_text()
                anim_start = hypr_content.find("# animation\n")
                deco_start = hypr_content.find("\n# deco")
                if anim_start != -1 and deco_start != -1:
                    hypr_content = hypr_content[:anim_start] + hypr_content[deco_start + 1:]
                    hypr_conf.write_text(hypr_content)
                    log_msg("Stripped animations — using Hyprland defaults")
                else:
                    log_msg("No animation section to strip", False)

        cli_menu_dst = LOCAL_BIN / "cli-menu.py" if state.rec_utils else None
        if cli_menu_dst and cli_menu_dst.exists():
            menu_content = cli_menu_dst.read_text()
            menu_content = menu_content.replace("__TERMINAL__", state.terminal_choice)
            cli_menu_dst.write_text(menu_content)
            log_msg("Patched cli-menu.py terminal references")

        if state.wallpaper_path:
            hp_cfg = XDG_CONFIG / "hypr" / "hyprpaper.conf"
            hp_cfg.write_text(
                f"preload = {state.wallpaper_path}\n"
                f"wallpaper = ,{state.wallpaper_path}\n"
            )
            log_msg("Created hyprpaper.conf with wallpaper")

        if state.rec_utils:
            LOCAL_BIN.mkdir(parents=True, exist_ok=True)

            for fname in ["cli-menu.py", "cli-search.py", "cli-launch.py"]:
                src = UTILS_DIR / fname
                dst = LOCAL_BIN / fname
                shutil.copy2(src, dst)
                dst.chmod(0o755)

            log_msg("Installed CLI utils to ~/.local/bin/")

            pip_cmd = [sys.executable, "-m", "pip", "install", "--user", "rapidfuzz"]
            r = subprocess.call(pip_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if r != 0:
                pip_cmd.append("--break-system-packages")
                r = subprocess.call(pip_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log_msg("Installed rapidfuzz (Python)", r == 0)

            if shutil.which("cargo"):
                r = subprocess.call(
                    ["cargo", "install", "eightfetch"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                log_msg("Installed eightfetch", r == 0)
            else:
                log_msg("cargo not found, skipping eightfetch", False)

            fish_cfg = XDG_CONFIG / "fish" / "config.fish"
            if fish_cfg.exists():
                content = fish_cfg.read_text()
                line = "fish_add_path ~/.cargo/bin\n"
                if line not in content:
                    content = line + content
                    fish_cfg.write_text(content)
                    log_msg("Added cargo bin to fish PATH")
        else:
            log_msg("Skipped utility installation", False)
    except Exception as e:
        log_msg(f"Error: {e}", False)

    log_y += 1
    done_msg = " Done! Press SPACE / ENTER to exit. "
    cx = (cols - len(done_msg)) // 2
    stdscr.addstr(log_y, cx, done_msg, THEME["success"] | curses.A_BOLD)
    log_y += 1
    quit_hint = "SUPER + M" if state.kb_mode == "my_binds" else "SUPER + C"
    hint_msg = f" Hint: quit Hyprland ({quit_hint}) and login again to apply changes. "
    cx = (cols - len(hint_msg)) // 2
    stdscr.addstr(log_y, cx, hint_msg, THEME["dim"])
    stdscr.refresh()
    await_key(stdscr)
    return True


def screen_cancelled(stdscr):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    box_w = min(44, cols - 4)
    box_h = 5
    bx = (cols - box_w) // 2
    by = (rows - box_h) // 2

    draw_box(stdscr, by, bx, box_h, box_w)

    msg = " Installation cancelled. No changes made. "
    cx = (cols - len(msg)) // 2
    stdscr.addstr(by + 2, cx, msg, THEME["error"])

    ex = " Press SPACE / ENTER to exit "
    cx = (cols - len(ex)) // 2
    stdscr.addstr(by + 3, cx, ex, THEME["dim"])

    curses.curs_set(0)
    stdscr.refresh()
    await_key(stdscr)


def main(stdscr):
    curses.curs_set(0)
    init_theme()

    state = InstallState()

    detect_os(state)
    check_deps(state)
    find_existing_configs(state)

    if not screen_welcome(stdscr):
        screen_cancelled(stdscr)
        return

    screen_os_check(stdscr, state)

    if not screen_kb_layout_prompt(stdscr, state):
        screen_cancelled(stdscr)
        return

    if not screen_dep_check(stdscr, state):
        screen_cancelled(stdscr)
        return

    if not screen_blur_prompt(stdscr, state):
        screen_cancelled(stdscr)
        return

    if not screen_rec_utils_prompt(stdscr, state):
        screen_cancelled(stdscr)
        return

    if not screen_terminal_prompt(stdscr, state):
        screen_cancelled(stdscr)
        return

    if not screen_bindings_prompt(stdscr, state):
        screen_cancelled(stdscr)
        return

    if not screen_animations_prompt(stdscr, state):
        screen_cancelled(stdscr)
        return

    if not screen_wallpaper_prompt(stdscr, state):
        screen_cancelled(stdscr)
        return

    if not screen_existing_configs(stdscr, state):
        screen_cancelled(stdscr)
        return

    if not screen_summary(stdscr, state):
        return

    screen_installing(stdscr, state)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
