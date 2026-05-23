#!/usr/bin/env python3

import curses
import re
import subprocess
import urllib.parse


def is_url(text: str) -> bool:
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text):
        return True
    if " " in text:
        return False
    if "." in text and not text.endswith("."):
        return True
    return False


def main(stdscr):
    curses.curs_set(1)
    curses.use_default_colors()

    query = ""

    while True:
        stdscr.erase()
        rows, cols = stdscr.getmaxyx()

        box_w = min(60, cols - 4)
        box_x = (cols - box_w) // 2
        box_y = rows // 2 - 1

        if box_y < 0:
            box_y = 0

        inner_w = box_w - 4

        stdscr.addstr(box_y, box_x, "┌" + "─" * (box_w - 2) + "┐")
        stdscr.addstr(box_y + 2, box_x, "└" + "─" * (box_w - 2) + "┘")

        line = "│ " + " " * inner_w + " │"
        stdscr.addstr(box_y + 1, box_x, line)

        if query:
            stdscr.addstr(box_y + 1, box_x + 2, query[:inner_w])
        else:
            stdscr.addstr(box_y + 1, box_x + 2, "Search..", curses.A_DIM)

        cursor_x = box_x + 2 + len(query)
        stdscr.move(box_y + 1, min(cursor_x, cols - 1))
        stdscr.refresh()

        key = stdscr.getch()

        if key in (curses.KEY_ENTER, 10, 13):
            break
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            query = query[:-1]
        elif key in (27, 3, 4):
            return
        elif key == curses.KEY_RESIZE:
            pass
        elif 32 <= key <= 126:
            query += chr(key)

    if not query:
        return

    if is_url(query):
        url = query
    else:
        url = "https://www.google.com/search?q=" + urllib.parse.quote(query)

    subprocess.Popen(
        ["zen-browser", url],
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
