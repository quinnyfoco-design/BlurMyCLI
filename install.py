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
        ("fish",    XDG_CONFIG / "fish" / "config.fish"),
        ("opencode", XDG_CONFIG / "opencode" / "opencode.jsonc"),
        ("opencode", XDG_CONFIG / "opencode" / "tui.json"),
    ]
    seen = set()
    for name, path in checks:
        if path.exists() and name not in seen:
            seen.add(name)
            state.existing_dirs.append(name)


def draw_footer(stdscr, text):
    rows, cols = stdscr.getmaxyx()
    if cols < 4:
        return
    stdscr.addstr(rows - 1, 0, "\u2502", curses.A_DIM)
    stdscr.addstr(rows - 1, 2, text[:cols - 4], curses.A_DIM)
    if cols - 1 > 2:
        try:
            x = min(cols - 2, len(text) + 2)
            stdscr.addstr(rows - 1, max(x, 2), "\u2502", curses.A_DIM)
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

    lines = [
        "",
        f"   {TITLE}   ",
        f"   {VERSION}   ",
        "",
        "   A CLI-focused Hyprland dotfile setup   ",
        "",
        "   Press SPACE / ENTER to begin...   ",
        "   Press ESC / Q to quit   ",
    ]
    start = max(0, (rows - len(lines)) // 2)
    for i, line in enumerate(lines):
        attr = curses.A_BOLD if "BlurMyCLI" in line else 0
        x = max(0, (cols - len(line)) // 2)
        stdscr.addstr(start + i, x, line, attr)

    curses.curs_set(0)
    stdscr.refresh()

    while True:
        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            continue
        if key in (10, 13, 32):
            return True
        if key in (27, ord("q"), ord("Q")):
            return False


def screen_os_check(stdscr, state: InstallState):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    y = 3
    stdscr.addstr(y, 2, "OS Detection", curses.A_BOLD)
    y += 1
    sep = min(40, cols - 4)
    stdscr.addstr(y, 2, "\u2500" * sep, curses.A_DIM)
    y += 2
    stdscr.addstr(y, 2, f"  Detected: {state.os_name}")
    y += 1
    if state.is_arch:
        stdscr.addstr(y, 2, "  Good, Arch Linux detected.", curses.A_BOLD)
    else:
        stdscr.addstr(y, 2, f"  Warning: {state.os_name} may not be fully compatible.", curses.A_BOLD)
        y += 1
        stdscr.addstr(y, 2, "  Things may not work out of the box.", curses.A_DIM)

    draw_footer(stdscr, "Press SPACE / ENTER to continue...")
    curses.curs_set(0)
    stdscr.refresh()
    await_key(stdscr)


def screen_kb_layout_prompt(stdscr, state: InstallState):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    lines = [
        "",
        "   Keyboard Layout   ",
        "",
        "   Enter your keyboard layout code",
        "   (e.g. us, de, fr, gb, jp, etc.)",
        "",
    ]
    start = max(2, (rows - len(lines) - 5) // 2)
    for i, line in enumerate(lines):
        attr = curses.A_BOLD if "Keyboard" in line else 0
        x = max(0, (cols - len(line)) // 2)
        stdscr.addstr(start + i, x, line, attr)

    path = state.kb_layout
    y = start + len(lines)
    sep = min(40, cols - 4)
    stdscr.addstr(y, 2, "\u2500" * sep, curses.A_DIM)
    y += 2

    curses.curs_set(1)

    while True:
        stdscr.addstr(y, 2, "  " + " " * max(cols - 4, 1))
        stdscr.addstr(y, 2, f"  Layout: {path}")
        stdscr.move(y, 10 + len(path))
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            rows, cols = stdscr.getmaxyx()
            continue
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

    y = 3
    stdscr.addstr(y, 2, "Dependency Check", curses.A_BOLD)
    y += 1
    sep = min(40, cols - 4)
    stdscr.addstr(y, 2, "\u2500" * sep, curses.A_DIM)
    y += 2

    scroll = 0
    max_visible = rows - y - 3

    while True:
        stdscr.erase()
        y = 3
        stdscr.addstr(y, 2, "Dependency Check", curses.A_BOLD)
        y += 1
        stdscr.addstr(y, 2, "\u2500" * min(40, cols - 4), curses.A_DIM)
        y += 2

        visible = state.dep_results[scroll:scroll + max_visible]
        for i, (name, found) in enumerate(visible):
            icon = "\u2713" if found else "\u2717"
            icon_attr = curses.color_pair(2) if found else curses.color_pair(1)
            label = f"  {icon}  {name}"
            stdscr.addstr(y + i, 2, label, icon_attr)

        total = len(state.dep_results)
        if total > max_visible:
            pct = f"  [{scroll + 1}-{min(scroll + max_visible, total)}/{total}]"
            stdscr.addstr(rows - 2, cols - len(pct) - 2, pct, curses.A_DIM)

        draw_footer(stdscr, "\u2191\u2195 scroll  Press SPACE / ENTER to continue...")
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            rows, cols = stdscr.getmaxyx()
            max_visible = rows - 6
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

    lines = [
        "",
        "   Blur Configuration   ",
        "",
        "   Enable blur effects in Hyprland?",
        "   (adds glass-like transparency to windows)",
        "",
    ]
    start = max(2, (rows - len(lines) - 4) // 2)
    for i, line in enumerate(lines):
        attr = curses.A_BOLD if "Blur Configuration" in line else 0
        x = max(0, (cols - len(line)) // 2)
        stdscr.addstr(start + i, x, line, attr)

    choice = state.blur
    while True:
        y = start + len(lines)
        yes_attr = curses.A_REVERSE if choice else 0
        no_attr = curses.A_REVERSE if not choice else 0
        sep = min(30, cols - 4)
        stdscr.addstr(y, 2, "\u2500" * sep, curses.A_DIM)
        y += 1
        stdscr.addstr(y, 4, "[Y]  Yes  ", yes_attr)
        stdscr.addstr(y, 14, "[N]  No  ", no_attr)
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            continue
        if key in (ord("y"), ord("Y"), curses.KEY_LEFT):
            choice = True
        elif key in (ord("n"), ord("N"), curses.KEY_RIGHT):
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

    lines = [
        "",
        "   Recommended Utilities   ",
        "",
        "   Install CLI tools + eightfetch?",
        "   (cli-menu, cli-search, cli-launch,",
        "    rapidfuzz, eightfetch)",
        "",
    ]
    start = max(2, (rows - len(lines) - 4) // 2)
    for i, line in enumerate(lines):
        attr = curses.A_BOLD if "Recommended Utilities" in line else 0
        x = max(0, (cols - len(line)) // 2)
        stdscr.addstr(start + i, x, line, attr)

    choice = state.rec_utils
    while True:
        y = start + len(lines)
        sep = min(30, cols - 4)
        stdscr.addstr(y, 2, "\u2500" * sep, curses.A_DIM)
        y += 1
        yes_attr = curses.A_REVERSE if choice else 0
        no_attr = curses.A_REVERSE if not choice else 0
        stdscr.addstr(y, 4, "[Y]  Yes  ", yes_attr)
        stdscr.addstr(y, 14, "[N]  No  ", no_attr)
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            continue
        if key in (ord("y"), ord("Y"), curses.KEY_LEFT):
            choice = True
        elif key in (ord("n"), ord("N"), curses.KEY_RIGHT):
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

    lines = [
        "",
        "   Wallpaper Setup   ",
        "",
        "   Enter path to a wallpaper image, or",
        "   leave empty and press ENTER to skip.",
        "",
    ]
    start = max(2, (rows - len(lines) - 5) // 2)
    for i, line in enumerate(lines):
        attr = curses.A_BOLD if "Wallpaper" in line else 0
        x = max(0, (cols - len(line)) // 2)
        stdscr.addstr(start + i, x, line, attr)

    path = ""
    y = start + len(lines)
    sep = min(40, cols - 4)
    stdscr.addstr(y, 2, "\u2500" * sep, curses.A_DIM)
    y += 2

    curses.curs_set(1)
    IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

    while True:
        stdscr.addstr(y, 2, "  " + " " * max(cols - 4, 1))
        stdscr.addstr(y, 2, f"  Path: {path}")
        help_y = y + 1
        stdscr.addstr(help_y, 2, "  " + " " * max(cols - 4, 1))

        trimmed = path.strip()
        if trimmed:
            p = Path(trimmed).expanduser()
            if not p.exists():
                stdscr.addstr(help_y, 2, "  File not found. Press ENTER to skip or fix the path.", curses.color_pair(1))
            elif p.suffix.lower() not in IMAGE_EXTS:
                stdscr.addstr(help_y, 2, "  Unsupported format (use png/jpg/webp/bmp). Press ENTER to skip.", curses.color_pair(1))

        stdscr.move(y, 8 + len(path))
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            rows, cols = stdscr.getmaxyx()
            continue
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


def screen_existing_configs(stdscr, state: InstallState):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    y = 3
    stdscr.addstr(y, 2, "Existing Configurations", curses.A_BOLD)
    y += 1
    sep = min(40, cols - 4)
    stdscr.addstr(y, 2, "\u2500" * sep, curses.A_DIM)
    y += 2

    if not state.existing_dirs:
        stdscr.addstr(y, 2, "  No existing configs found. Fresh install!")
        draw_footer(stdscr, "Press SPACE / ENTER to continue...")
        stdscr.refresh()
        await_key(stdscr)
        return True

    for name in state.existing_dirs:
        stdscr.addstr(y, 2, f"  Found: ~/.config/{name}/")
        y += 1

    y += 1
    stdscr.addstr(y, 2, "  How to handle existing files?")
    y += 1

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
        y = 3
        stdscr.addstr(y, 2, "Existing Configurations", curses.A_BOLD)
        y += 1
        stdscr.addstr(y, 2, "\u2500" * min(40, cols - 4), curses.A_DIM)
        y += 2
        for name in state.existing_dirs:
            stdscr.addstr(y, 2, f"  Found: ~/.config/{name}/")
            y += 1
        y += 1
        stdscr.addstr(y, 2, "  How to handle existing files?")
        y += 1

        for i, (key, label, _) in enumerate(options):
            attr = curses.A_REVERSE if i == choice_idx else 0
            stdscr.addstr(y, 4, f"[{key}]  {label}", attr)
            y += 1

        draw_footer(stdscr, "\u2191\u2195  Select  SPACE / ENTER to confirm")
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

    action_labels = {"bak": "backup + overwrite", "overwrite": "overwrite", "skip": "skip"}
    config_text = action_labels.get(state.config_action, state.config_action)
    wall_text = state.wallpaper_path if state.wallpaper_path else "none"

    lines = [
        "",
        "   Installation Summary   ",
        "",
        f"   OS:           {state.os_name}",
        f"   Keyboard:     {state.kb_layout}",
        f"   Missing:      {', '.join(missing) if missing else 'none'}",
        f"   Blur:         {blur_text}",
        f"   Rec utils:    {rec_text}",
        f"   Wallpaper:    {wall_text}",
        f"   Existing:     {config_text}",
        "",
    ]

    start = max(2, (rows - len(lines) - 4) // 2)
    for i, line in enumerate(lines):
        attr = curses.A_BOLD if "Summary" in line else 0
        x = max(0, (cols - len(line)) // 2)
        stdscr.addstr(start + i, x, line, attr)

    sep = min(40, cols - 4)

    choice = True
    while True:
        y = start + len(lines) + 1
        stdscr.addstr(y, 2, "\u2500" * sep, curses.A_DIM)
        y += 1
        stdscr.addstr(y, 4, "  Does this look right?  ", curses.A_BOLD)
        y += 1
        yes_attr = curses.A_REVERSE if choice else 0
        no_attr = curses.A_REVERSE if not choice else 0
        stdscr.addstr(y, 4, "[Y]  Yes, install!  ", yes_attr)
        stdscr.addstr(y, 24, "[N]  No, cancel  ", no_attr)
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            continue
        if key in (ord("y"), ord("Y"), curses.KEY_LEFT):
            choice = True
        elif key in (ord("n"), ord("N"), curses.KEY_RIGHT):
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

    lines = [
        "",
        "   Installing...   ",
        "",
    ]
    start = 3
    for i, line in enumerate(lines):
        attr = curses.A_BOLD if "Installing" in line else 0
        x = max(0, (cols - len(line)) // 2)
        stdscr.addstr(start + i, x, line, attr)

    log_y = start + len(lines) + 1
    log = []

    def log_msg(msg, ok=True):
        nonlocal log_y
        icon = "\u2713" if ok else "\u2717"
        attr = curses.color_pair(2) if ok else curses.color_pair(1)
        stdscr.addstr(log_y, 2, f"  {icon}  {msg}", attr)
        log_y += 1
        stdscr.refresh()

    stdscr.refresh()

    try:
        config_mapping = [
            ("hypr",    "hyprland.conf"),
            ("kitty",   "kitty.conf"),
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
            }
            for old, new in replacements.items():
                content = content.replace(old, new)

            if not state.blur:
                content = content.replace("enabled = true", "enabled = false")

            if state.wallpaper_path:
                if "exec-once = hyprpaper" not in content:
                    content = content.replace(
                        "exec-once = hyprsunset",
                        "exec-once = hyprpaper &\nexec-once = hyprsunset",
                    )

            hypr_conf.write_text(content)
            log_msg("Patched hyprland.conf (paths + blur setting)")

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
    stdscr.addstr(log_y, 2, "  Done! Press SPACE / ENTER to exit.", curses.A_BOLD)
    log_y += 1
    stdscr.addstr(log_y, 2, "  Hint: quit Hyprland (SUPER + M) and login again to apply changes.", curses.A_DIM)
    stdscr.refresh()
    await_key(stdscr)
    return True


def screen_cancelled(stdscr):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()

    lines = [
        "",
        "   Installation cancelled.   ",
        "   No changes were made.   ",
        "",
        "   Press SPACE / ENTER to exit.   ",
    ]
    start = max(2, (rows - len(lines)) // 2)
    for i, line in enumerate(lines):
        x = max(0, (cols - len(line)) // 2)
        stdscr.addstr(start + i, x, line)

    draw_footer(stdscr, "")
    curses.curs_set(0)
    stdscr.refresh()
    await_key(stdscr)


def main(stdscr):
    curses.curs_set(0)
    curses.use_default_colors()
    if curses.has_colors():
        curses.init_pair(1, curses.COLOR_RED, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)

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
