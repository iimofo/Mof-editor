import curses
import re
import tkinter as tk
from tkinter import filedialog

# Define enhanced syntax highlighting rules
SYNTAX_PATTERNS = [
    (re.compile(r'\b(def|class|if|else|elif|for|while|return|import|from|as|try|except|finally|with|yield|break|continue|pass|global|nonlocal|assert|lambda|del|True|False|None|and|or|not|is|in|raise|print|input|self|super)\b'), 1),  # Keywords
    (re.compile(r'#[^\n]*'), 2),  # Comments
    (re.compile(r'\"\"\".*?\"\"\"|\'\'\'.*?\'\'\'|\".*?\"|\'.*?\''), 3),  # Strings
    (re.compile(r'\b\d+\b'), 4),  # Numbers
    (re.compile(r'\b[A-Za-z_][A-Za-z0-9_]*\b'), 5),  # Identifiers (variables, functions)
    (re.compile(r'[\+\-\*/=<>!&|%^~]+'), 6),  # Operators
]

# Define color pairs
COLORS = {
    1: (curses.COLOR_BLUE, curses.COLOR_BLACK),    # Keywords
    2: (curses.COLOR_GREEN, curses.COLOR_BLACK),   # Comments
    3: (curses.COLOR_YELLOW, curses.COLOR_BLACK),  # Strings
    4: (curses.COLOR_CYAN, curses.COLOR_BLACK),    # Numbers
    5: (curses.COLOR_MAGENTA, curses.COLOR_BLACK), # Identifiers
    6: (curses.COLOR_RED, curses.COLOR_BLACK),     # Operators
    8: (curses.COLOR_BLACK, curses.COLOR_WHITE),   # Cursor
}

def draw_status_bar(stdscr, status):
    height, width = stdscr.getmaxyx()
    stdscr.attron(curses.color_pair(7))
    stdscr.addstr(height-1, 0, status)
    stdscr.addstr(height-1, len(status), " " * (width - len(status) - 1))
    stdscr.attroff(curses.color_pair(7))

def apply_syntax_highlighting(stdscr, line, y, offset_x, cursor_pos=None):
    stdscr.addstr(y, 0, line[offset_x:])
    for pattern, color in SYNTAX_PATTERNS:
        for match in pattern.finditer(line):
            start, end = match.span()
            if start >= offset_x and start - offset_x < curses.COLS:
                stdscr.addstr(y, start - offset_x, line[start:end], curses.color_pair(color))
    
    if cursor_pos is not None:
        cursor_x = cursor_pos - offset_x
        if 0 <= cursor_x < len(line) - offset_x:
            stdscr.addstr(y, cursor_x, line[cursor_pos], curses.color_pair(8))

def main(stdscr):
    curses.curs_set(0)  # Hide the default cursor
    curses.start_color()
    
    # Initialize color pairs
    for i, (fg, bg) in COLORS.items():
        curses.init_pair(i, fg, bg)
    curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_CYAN)
    
    height, width = stdscr.getmaxyx()
    
    cursor_x = 0
    cursor_y = 0
    offset_x = 0
    offset_y = 0
    
    text_lines = [""]
    status = "Press ESC to exit | F2 to save | F3 to open | Ctrl+Z to undo | Ctrl+Y to redo"
    file_name = "untitled.txt"
    
    undo_stack = []
    redo_stack = []

    def save_undo():
        undo_stack.append((cursor_y, cursor_x, [line[:] for line in text_lines]))
        if len(undo_stack) > 50:  # Limit stack size
            undo_stack.pop(0)
        redo_stack.clear()  # Clear redo stack on new action

    def redraw_screen():
        stdscr.clear()
        for idx, line in enumerate(text_lines[offset_y:offset_y + height - 1]):
            apply_syntax_highlighting(stdscr, line, idx, offset_x, cursor_pos=cursor_x if idx == cursor_y - offset_y else None)
        draw_status_bar(stdscr, status)
        stdscr.refresh()

    def handle_keypress(key, file_name):
        nonlocal cursor_x, cursor_y, offset_x, offset_y, status, text_lines
        
        if key == curses.KEY_RIGHT:
            if cursor_x < len(text_lines[cursor_y]):
                cursor_x += 1
            elif cursor_y < len(text_lines) - 1:
                cursor_x = 0
                cursor_y += 1
        elif key == curses.KEY_LEFT:
            if cursor_x > 0:
                cursor_x -= 1
            elif cursor_y > 0:
                cursor_y -= 1
                cursor_x = len(text_lines[cursor_y])
        elif key == curses.KEY_DOWN:
            if cursor_y < len(text_lines) - 1:
                cursor_y += 1
                cursor_x = min(cursor_x, len(text_lines[cursor_y]))
        elif key == curses.KEY_UP:
            if cursor_y > 0:
                cursor_y -= 1
                cursor_x = min(cursor_x, len(text_lines[cursor_y]))
        elif key == 127 or key == curses.KEY_BACKSPACE:  # Backspace
            if cursor_x > 0:
                save_undo()
                text_lines[cursor_y] = text_lines[cursor_y][:cursor_x-1] + text_lines[cursor_y][cursor_x:]
                cursor_x -= 1
            elif cursor_y > 0:
                save_undo()
                cursor_x = len(text_lines[cursor_y - 1])
                text_lines[cursor_y - 1] += text_lines[cursor_y]
                text_lines.pop(cursor_y)
                cursor_y -= 1
        elif key == 10:  # Enter
            save_undo()
            text_lines.insert(cursor_y + 1, text_lines[cursor_y][cursor_x:])
            text_lines[cursor_y] = text_lines[cursor_y][:cursor_x]
            cursor_y += 1
            cursor_x = 0
        elif key == 27:  # ESC key to exit
            return False, file_name
        elif key == curses.KEY_F2:  # F2 to save with a custom name
            curses.echo()
            stdscr.addstr(height-1, 0, "Save file as: ")
            new_file_name = stdscr.getstr(height-1, 13).decode("utf-8")
            curses.noecho()
            with open(new_file_name, "w") as f:
                f.write("\n".join(text_lines))
            status = f"File saved as {new_file_name}"
        elif key == curses.KEY_F3:  # F3 to open
            open_file_dialog(stdscr)
        elif key == 26:  # Ctrl+Z to undo
            if undo_stack:
                redo_stack.append((cursor_y, cursor_x, [line[:] for line in text_lines]))
                cursor_y, cursor_x, text_lines = undo_stack.pop()
                status = "Undone last action"
        elif key == 25:  # Ctrl+Y to redo
            if redo_stack:
                undo_stack.append((cursor_y, cursor_x, [line[:] for line in text_lines]))
                cursor_y, cursor_x, text_lines = redo_stack.pop()
                status = "Redone last action"
        else:
            save_undo()
            text_lines[cursor_y] = text_lines[cursor_y][:cursor_x] + chr(key) + text_lines[cursor_y][cursor_x:]
            cursor_x += 1

        if cursor_x - offset_x >= width - 5:
            offset_x += 1
        if cursor_x < offset_x:
            offset_x = max(0, cursor_x)
        if cursor_y - offset_y >= height - 1:
            offset_y += 1
        if cursor_y < offset_y:
            offset_y = max(0, cursor_y)
        
        return True, file_name

    def open_file_dialog(stdscr):
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        file_path = filedialog.askopenfilename()
        if file_path:
            try:
                with open(file_path, "r") as f:
                    text_lines.clear()
                    text_lines.extend(f.read().splitlines())
                cursor_x = cursor_y = offset_x = offset_y = 0
                status = f"File {file_path} opened"
            except FileNotFoundError:
                status = f"File {file_path} not found"

    while True:
        redraw_screen()
        key = stdscr.getch()
        running, file_name = handle_keypress(key, file_name)
        if not running:
            break

curses.wrapper(main)
