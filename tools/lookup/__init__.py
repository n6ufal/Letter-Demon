"""Dictionary Lookup — standalone tkinter app for word list exploration.

Uses binary search (bisect) for O(log n) prefix/suffix lookup on
a sorted word list. Runs independently of the main Letter Demon app.
"""

import ctypes
import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import tkinter as tk

from .app import LookupApp
from .log_setup import setup_logging

setup_logging(_PROJECT_ROOT)


def main():
    try:
        root = tk.Tk()
        LookupApp(root)
        root.mainloop()
    except Exception:
        import traceback
        error_msg = traceback.format_exc()
        import logging
        logging.critical("Startup crash:\n%s", error_msg)
        try:
            tk.Tk().withdraw()
            import tkinter.messagebox as mb
            mb.showerror("Startup Error", error_msg)
        except Exception:
            pass


if __name__ == "__main__":
    main()
