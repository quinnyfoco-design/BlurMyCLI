#!/usr/bin/env python3

import curses
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Item:
    name: str
    command: Optional[str] = None
    children: list['Item'] = field(default_factory=list)
    icon: str = ""
    comment: str = ""


PP_CMD = "powerprofilesctl set {}"


def menu() -> list[Item]:
    items = [
        Item("Apps", icon="\uf07c", comment="Launch applications", children=[
            Item("Files", "dolphin", icon="\uf07c", comment="File manager"),
            Item("Terminal", "kitty", icon="\uf489", comment="Terminal emulator"),
            Item("Browser", "zen-browser", icon="\uf269", comment="Web browser"),
            Item("Editor", "vim", icon="\uf4ae", comment="Text editor"),
            Item("Launcher", "wofi --show drun", icon="\uf002", comment="App launcher"),
        ]),
        Item("Power", icon="\uf011", comment="System power actions", children=[
            Item("Suspend", "systemctl suspend", icon="\uf186", comment="Sleep the system"),
            Item("Reboot", "systemctl reboot", icon="\uf021", comment="Restart"),
            Item("Shutdown", "systemctl poweroff", icon="\uf011", comment="Power off"),
            Item("Lock", "loginctl lock-session", icon="\uf023", comment="Lock screen"),
            Item("Log Out", "hyprctl dispatch exit", icon="\uf2f5", comment="End session"),
        ]),
        Item("Power Mode", icon="\uf0e7", comment="CPU / platform profile", children=[
            Item("Performance", PP_CMD.format("performance"), icon="\uf0e7", comment="Max speed"),
            Item("Balanced", PP_CMD.format("balanced"), icon="\uf04b", comment="Default"),
            Item("Power Saver", PP_CMD.format("power-saver"), icon="\uf186", comment="Save power"),
        ]),
        Item("Display", icon="\uf108", comment="Display settings", children=[
            Item("Night Light On", "hyprctl hyprsunset temperature 4000", icon="\uf185", comment="Warm colors"),
            Item("Night Light Off", "hyprctl hyprsunset identity", icon="\uf185", comment="Normal colors"),
        ]),
        Item("Style", icon="\uf1fc", comment="Theme and appearance", children=[
            Item("Dark Mode", "gsettings set org.gnome.desktop.interface color-scheme prefer-dark", icon="\uf186", comment="Dark theme"),
            Item("Light Mode", "gsettings set org.gnome.desktop.interface color-scheme prefer-light", icon="\uf185", comment="Light theme"),
        ]),
        Item("System", icon="\uf200", comment="System tools", children=[
            Item("Monitor", "kitty -e htop", icon="\uf200", comment="Process monitor"),
            Item("Network", "kitty -e nmtui", icon="\uf1eb", comment="Network manager"),
            Item("Config", "kitty -e vim ~/.config/hypr/hyprland.conf", icon="\uf013", comment="Edit hyprland.conf"),
        ]),
    ]

    pf = Path("/sys/firmware/acpi/platform_profile_choices")
    if pf.is_file():
        choices = pf.read_text().strip().split()
        items.insert(3, Item("Fan Profile", icon="\uf2f9", comment="Laptop fan speed curve", children=[
            Item(c, f"kitty -e sh -c 'echo {c} | sudo tee /sys/firmware/acpi/platform_profile && echo Done. Press any key... && read -n1'", icon="\uf2f9", comment=f"Set fan profile to {c}")
            for c in choices
        ]))

    return items


class Omarch:
    def __init__(self, stdscr, root: list[Item]):
        self.stdscr = stdscr
        self.root = root
        self.stack: list[list[Item]] = [root]
        self.breadcrumb: list[str] = []
        self.query = ""
        self.selected = 0
        self.scroll = 0
        self.filtered: list[Item] = []

        curses.curs_set(1)
        curses.use_default_colors()
        self.REV = curses.A_REVERSE
        self.DIM = curses.A_DIM

        self._refilter()

    def _items(self) -> list[Item]:
        return self.stack[-1]

    def _refilter(self):
        q = self.query.strip().lower()
        items = self._items()
        if not q:
            self.filtered = list(items)
        else:
            self.filtered = [
                it for it in items
                if q in it.name.lower() or q in it.comment.lower()
            ]
        self.selected = min(self.selected, max(0, len(self.filtered) - 1)) if self.filtered else 0
        self._clamp()

    def _clamp(self):
        rows, _ = self.stdscr.getmaxyx()
        vis = max(1, rows - 4)
        if self.selected < self.scroll:
            self.scroll = self.selected
        elif self.selected >= self.scroll + vis:
            self.scroll = self.selected - vis + 1
        self.scroll = max(0, min(self.scroll, max(0, len(self.filtered) - vis)))

    def _draw(self):
        self.stdscr.erase()
        rows, cols = self.stdscr.getmaxyx()

        # breadcrumb
        if rows > 0:
            parts = ["Menu"] + self.breadcrumb
            label = "  \u203a  ".join(parts)
            if len(label) > cols - 1:
                label = "\u2026" + label[-(cols - 2):]
            self.stdscr.addstr(0, 0, label, self.DIM)

        # search bar
        prompt = "> "
        if rows > 1:
            if self.query:
                self.stdscr.addstr(1, 0, prompt + self.query)
                cx = len(prompt) + len(self.query)
            else:
                self.stdscr.addstr(1, 0, prompt + "Search...", self.DIM)
                cx = len(prompt)

        # sep
        if rows > 2:
            self.stdscr.addstr(2, 0, "\u2500" * min(cols, 60), self.DIM)

        # items
        vis = max(1, rows - 4)

        # compute max prefix width for │ alignment
        max_prefix = 0
        for i in range(vis):
            idx = self.scroll + i
            if idx >= len(self.filtered):
                break
            it = self.filtered[idx]
            arrow = " \u25b6" if it.children else ""
            icon = f"{it.icon} " if it.icon else ""
            max_prefix = max(max_prefix, len(f" {icon}{it.name}{arrow}"))

        for i in range(vis):
            y = 3 + i
            idx = self.scroll + i
            if idx >= len(self.filtered):
                if i == 0 and not self.filtered:
                    self.stdscr.addstr(y, 0, "  No matches", self.DIM)
                break

            it = self.filtered[idx]
            attr = self.REV if idx == self.selected else 0
            arrow = " \u25b6" if it.children else ""
            icon = f"{it.icon} " if it.icon else ""
            prefix = f" {icon}{it.name}{arrow}"
            comment = f"  \u2502 {it.comment}" if it.comment else ""
            line = f"{prefix:<{max_prefix}}{comment}"
            if len(line) > cols - 1:
                line = line[:cols - 2] + "\u2026"
            self.stdscr.addstr(y, 0, line[:cols - 1], attr)

        # status bar
        if rows > 4:
            depth = len(self.stack)
            total = len(self._items())
            shown = len(self.filtered)
            hint = "\u2191\u2195 nav  Enter select  \u2190 Back  type filter"
            status = f" {shown}/{total}  |  {hint}"
            self.stdscr.addstr(rows - 1, 0, status[:cols - 1], self.DIM)

        if rows > 1:
            self.stdscr.move(1, min(cx, cols - 1))
        self.stdscr.refresh()

    def _go_back(self):
        if len(self.stack) > 1:
            self.stack.pop()
            self.breadcrumb.pop()
            self.query = ""
            self.selected = 0
            self.scroll = 0
            self._refilter()

    def run(self) -> Optional[str]:
        while True:
            self._draw()
            key = self.stdscr.getch()

            if key in (curses.KEY_ENTER, 10, 13):
                if not self.filtered:
                    continue
                it = self.filtered[self.selected]
                if it.children:
                    self.stack.append(it.children)
                    self.breadcrumb.append(it.name)
                    self.query = ""
                    self.selected = 0
                    self.scroll = 0
                    self._refilter()
                elif it.command:
                    return it.command
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                if self.query:
                    self.query = self.query[:-1]
                    self.selected = 0
                    self.scroll = 0
                    self._refilter()
                else:
                    self._go_back()
            elif key == curses.KEY_LEFT:
                self._go_back()
            elif key == curses.KEY_RIGHT:
                if self.filtered:
                    it = self.filtered[self.selected]
                    if it.children:
                        self.stack.append(it.children)
                        self.breadcrumb.append(it.name)
                        self.query = ""
                        self.selected = 0
                        self.scroll = 0
                        self._refilter()
            elif key == curses.KEY_DOWN:
                if self.filtered:
                    self.selected = min(self.selected + 1, len(self.filtered) - 1)
                    self._clamp()
            elif key == curses.KEY_UP:
                self.selected = max(self.selected - 1, 0)
                self._clamp()
            elif key in (curses.KEY_NPAGE,):
                rows, _ = self.stdscr.getmaxyx()
                vis = max(1, rows - 4)
                if self.filtered:
                    self.selected = min(self.selected + vis, len(self.filtered) - 1)
                    self._clamp()
            elif key in (curses.KEY_PPAGE,):
                rows, _ = self.stdscr.getmaxyx()
                vis = max(1, rows - 4)
                self.selected = max(self.selected - vis, 0)
                self._clamp()
            elif key in (27, 3, 4):
                return None
            elif key == curses.KEY_RESIZE:
                pass
            elif 32 <= key <= 126:
                self.query += chr(key)
                self.selected = 0
                self.scroll = 0
                self._refilter()


def main(stdscr):
    items = menu()
    app = Omarch(stdscr, items)
    cmd = app.run()
    if cmd:
        subprocess.Popen(
            cmd,
            shell=True,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
