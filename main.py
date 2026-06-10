"""Letter Demon — Debug entry point (shows console).

Run this instead of main.pyw to see errors printed to the terminal:
    python main.py
"""

import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import logging
log_dir = os.path.join(_PROJECT_ROOT, "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, "letter_demon.log"), mode="a", encoding="utf-8"),
    ],
)

import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import tkinter as tk


def main() -> None:
    from ui.app import LetterDemonApp
    root = tk.Tk()
    LetterDemonApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
