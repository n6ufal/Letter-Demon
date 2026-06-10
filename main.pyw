"""Letter Demon — Entry point.

Run this file to launch the application:
    python main.pyw
"""

import os
import sys

# Ensure the project root is on sys.path
# This is critical when double-clicking the .pyw file from Explorer,
# because the working directory may not be the script's directory.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import logging
log_dir = os.path.join(_PROJECT_ROOT, "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "letter_demon.log"), mode="a", encoding="utf-8"),
    ],
)
log_path = os.path.join(log_dir, "letter_demon.log")

import ctypes

# HiDPI — must run before any window is created
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
    try:
        main()
    except Exception:
        logging.exception("Unhandled exception at startup")
        try:
            import tkinter.messagebox as mb
            root = tk.Tk()
            root.withdraw()
            mb.showerror(
                "Letter Demon — Startup Error",
                f"An error occurred.\n\nDetails written to:\n{log_path}",
            )
        except Exception:
            pass
