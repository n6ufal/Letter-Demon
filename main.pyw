"""Letter Demon — Entry point.

Run this file to launch the application:
    python main.pyw
"""

import os
import sys

# Ensure the project root (letter_demon/) is on sys.path
# This is critical when double-clicking the .pyw file from Explorer,
# because the working directory may not be the script's directory.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import ctypes

# HiDPI — must run before any window is created
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
    try:
        main()
    except Exception as e:
        # .pyw suppresses console output — write crash info to a log file
        import traceback
        log_path = os.path.join(_PROJECT_ROOT, "crash.log")
        with open(log_path, "w") as f:
            f.write(traceback.format_exc())
        # Also show a messagebox so the user sees something
        try:
            import tkinter.messagebox as mb
            root = tk.Tk()
            root.withdraw()
            mb.showerror(
                "Letter Demon — Startup Error",
                f"{type(e).__name__}: {e}\n\n"
                f"Details saved to:\n{log_path}",
            )
        except Exception:
            pass
