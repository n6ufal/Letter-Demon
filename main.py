"""Letter Demon — Debug entry point (shows console).

Run this instead of main.pyw to see errors printed to the terminal:
    python main.py
"""

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import logging
log_dir = Path(_PROJECT_ROOT) / "data" / "runtime" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(log_dir / "letter_demon.log"), mode="a", encoding="utf-8"),
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
