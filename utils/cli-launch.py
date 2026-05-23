#!/usr/bin/env python3

import curses
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz, process


@dataclass
class App:
    name: str
    exec_cmd: str
    comment: str = ""
    icon: str = ""


DESKTOP_DIRS = [
    Path.home() / ".local/share/applications",
    Path("/usr/share/applications"),
    Path("/usr/local/share/applications"),
    Path.home() / ".nix-profile/share/applications",
]

FIELD_CODE_RE = re.compile(r"%[fFuUdDnNickvm]")


def parse_desktop_file(path: Path) -> Optional[App]:
    if not path.is_file():
        return None
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    if "[Desktop Entry]" not in content:
        return None

    entries: dict[str, str] = {}
    section = None
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if section != "Desktop Entry":
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        entries[key.strip()] = val.strip()

    if entries.get("Type") != "Application":
        return None
    if entries.get("NoDisplay", "").lower() == "true":
        return None

    name = entries.get("Name")
    if not name:
        return None

    lang = os.environ.get("LANG", "")
    if lang:
        lang_variants = [lang.split(".")[0], lang[:2]]
        for variant in lang_variants:
            localized = entries.get(f"Name[{variant}]")
            if localized:
                name = localized
                break

    exec_cmd = entries.get("Exec", "")
    exec_cmd = FIELD_CODE_RE.sub("", exec_cmd).strip()
    if not exec_cmd:
        return None

    comment = entries.get("Comment", "")
    if lang:
        lang_variants = [lang.split(".")[0], lang[:2]]
        for variant in lang_variants:
            localized = entries.get(f"Comment[{variant}]")
            if localized:
                comment = localized
                break

    return App(
        name=name,
        exec_cmd=exec_cmd,
        comment=comment,
        icon=entries.get("Icon", ""),
    )


def discover_apps() -> list[App]:
    seen: set[str] = set()
    apps: list[App] = []
    for d in DESKTOP_DIRS:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.desktop")):
            app = parse_desktop_file(f)
            if app and app.exec_cmd not in seen:
                seen.add(app.exec_cmd)
                apps.append(app)
    apps.sort(key=lambda a: a.name.lower())
    return apps


class Searcher:
    def __init__(self, apps: list[App]):
        self.apps = apps
        self.names = [a.name for a in apps]

    def search(self, query: str, limit: int = 30) -> list[tuple[App, float]]:
        if not query:
            return [(app, 100.0) for app in self.apps[:limit]]
        results = process.extract(
            query,
            self.names,
            scorer=fuzz.WRatio,
            limit=limit,
            score_cutoff=25,
        )
        return [(self.apps[idx], score) for _, score, idx in results]

    def best_suggestion(self, query: str) -> Optional[str]:
        if not query or not self.apps:
            return None
        results = process.extract(
            query,
            self.names,
            scorer=fuzz.WRatio,
            limit=1,
            score_cutoff=40,
        )
        if not results:
            return None
        best_name, _, _ = results[0]
        if best_name.lower().startswith(query.lower()):
            return best_name[len(query):]
        return None


class CursesUI:
    def __init__(self, stdscr, apps: list[App]):
        self.stdscr = stdscr
        self.searcher = Searcher(apps)
        self.query = ""
        self.selected = 0
        self.scroll_offset = 0
        self.results: list[tuple[App, float]] = []
        self.suggestion = ""

        curses.curs_set(1)
        curses.use_default_colors()
        self.SELECTED = curses.A_REVERSE
        self.DIM = curses.A_DIM

    def run(self):
        self._search()
        while True:
            self._draw()
            key = self.stdscr.getch()
            if not self._handle_key(key):
                break

    def _search(self):
        self.results = self.searcher.search(self.query)
        if self.results:
            self.selected = min(self.selected, len(self.results) - 1)
        else:
            self.selected = 0
        self.suggestion = self.searcher.best_suggestion(self.query) or ""
        self._clamp_scroll()

    def _clamp_scroll(self):
        rows, _ = self.stdscr.getmaxyx()
        visible = max(1, rows - 3)
        if self.selected < self.scroll_offset:
            self.scroll_offset = self.selected
        elif self.selected >= self.scroll_offset + visible:
            self.scroll_offset = self.selected - visible + 1
        self.scroll_offset = max(0, min(self.scroll_offset, max(0, len(self.results) - visible)))

    def _draw(self):
        self.stdscr.erase()
        rows, cols = self.stdscr.getmaxyx()

        prompt = "> "
        typed = self.query
        suffix = self.suggestion

        typed_shown = typed
        suffix_shown = suffix

        max_input = cols - len(prompt) - 1
        if len(typed) + len(suffix) > max_input:
            extra = len(typed) + len(suffix) - max_input
            if extra < len(typed):
                typed_shown = typed[extra:]
            else:
                typed_shown = ""
                suffix_shown = suffix[extra - len(typed):]

        self.stdscr.addstr(0, 0, prompt)
        self.stdscr.addstr(0, len(prompt), typed_shown)
        if suffix_shown:
            self.stdscr.addstr(0, len(prompt) + len(typed_shown), suffix_shown, self.DIM)

        if rows > 2:
            sep_end = min(cols, 40)
            self.stdscr.addstr(1, 0, "─" * sep_end, self.DIM)

        visible = max(1, rows - 3)
        for i in range(visible):
            y = 2 + i
            idx = self.scroll_offset + i
            if idx >= len(self.results):
                if self.results:
                    break
                if i == 0 and not self.query:
                    self.stdscr.addstr(y, 0, "  No applications found", self.DIM)
                elif i == 0:
                    self.stdscr.addstr(y, 0, "  No matches", self.DIM)
                break

            app, score = self.results[idx]
            max_name_w = max(10, cols - 8)
            name = app.name[:max_name_w - 1] + "…" if len(app.name) > max_name_w else app.name

            score_str = f"{int(score)}%"
            pad = max(1, cols - len(name) - len(score_str) - 2)
            line = f" {name}{' ' * pad}{score_str}"

            attr = self.SELECTED if idx == self.selected else 0
            self.stdscr.addstr(y, 0, line[:cols - 1], attr)

        if rows > 2:
            status = f" {len(self.results)} result{'s' if len(self.results) != 1 else ''}"
            self.stdscr.addstr(rows - 1, 0, status[:cols - 1], self.DIM)

        cursor_x = len(prompt) + len(typed)
        self.stdscr.move(0, min(cursor_x, cols - 1))
        self.stdscr.refresh()

    def _handle_key(self, key) -> bool:
        if key in (curses.KEY_ENTER, 10, 13):
            self._launch()
            return False
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            self.query = self.query[:-1]
            self._search()
        elif key == curses.KEY_DOWN:
            if self.results:
                self.selected = min(self.selected + 1, len(self.results) - 1)
                self._clamp_scroll()
        elif key == curses.KEY_UP:
            self.selected = max(self.selected - 1, 0)
            self._clamp_scroll()
        elif key in (curses.KEY_RIGHT, 9):
            self._accept_suggestion()
        elif key in (27, 3, 4):
            return False
        elif key == curses.KEY_RESIZE:
            pass
        elif 32 <= key <= 126:
            self.query += chr(key)
            self._search()
        return True

    def _accept_suggestion(self):
        if self.suggestion:
            self.query += self.suggestion
            self._search()

    def _launch(self):
        if not self.results:
            return
        self._launch_cmd = self.results[self.selected][0].exec_cmd

    @property
    def launch_cmd(self):
        return getattr(self, "_launch_cmd", None)



def main(stdscr):
    apps = discover_apps()
    if not apps:
        stdscr.addstr(0, 0, "No .desktop files found.")
        stdscr.addstr(1, 0, "Check DESKTOP_DIRS or install some apps.")
        stdscr.refresh()
        stdscr.getch()
        return
    ui = CursesUI(stdscr, apps)
    ui.run()
    cmd = ui.launch_cmd
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
