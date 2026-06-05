"""Small Tk helpers shared by dialogs and editors."""

import tkinter as tk


def center_window(win: tk.Toplevel, parent: tk.Misc | None = None) -> None:
    win.update_idletasks()
    w = win.winfo_width()
    h = win.winfo_height()
    if parent is not None and parent.winfo_exists():
        px = parent.winfo_x()
        py = parent.winfo_y()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = px + (pw // 2) - (w // 2)
        y = py + (ph // 2) - (h // 2)
    else:
        x = (win.winfo_screenwidth() // 2) - (w // 2)
        y = (win.winfo_screenheight() // 2) - (h // 2)
    win.geometry(f"+{x}+{y}")
