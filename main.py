"""Letter Demon — Debug entry point (shows console).

Run this instead of main.pyw to see errors printed to the terminal:
    python main.py
"""

import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import tkinter as tk


def main() -> None:
    from ui.app import LastLetterApp
    root = tk.Tk()
    LastLetterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
