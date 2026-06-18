"""Dictionary Lookup — standalone tkinter app for word list exploration.

Uses binary search (bisect) for O(log n) prefix/suffix lookup on
a sorted word list. Runs independently of the main Letter Demon app.
"""

import json
import logging
import sys
import threading
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

log_dir = Path(_PROJECT_ROOT) / "data" / "runtime" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(log_dir / "lookup.log"), mode="a", encoding="utf-8"),
    ],
)

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core.dict_lookup import DictLookup
from core.dictionary import load_wordlist_from_dict
from core import __version__
from config.exceptions import load_exceptions as _load_exc, save_exceptions as _save_exc

logger = logging.getLogger(__name__)

SETTINGS_FILE = Path(_PROJECT_ROOT) / "data" / "runtime" / "lookup_settings.json"


class DictionaryLookupApp:

    RESULT_LIMIT = 500

    def __init__(self, root):
        self.root = root
        self.root.title(f"Dictionary Lookup v{__version__}")
        self.root.minsize(800, 500)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.dict_path = None
        self.lookup = DictLookup()
        self.exceptions = set()
        self._search_after_id = None

        self._build_ui()
        self._setup_protocols()
        self._load_settings()
        self._center_window()
        self._load_exceptions()

        if self.dict_path and Path(self.dict_path).is_file():
            self._load_dictionary(self.dict_path)

    def _center_window(self):
        self.root.update_idletasks()
        w, h = 1000, 620
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)

        self._build_dict_bar(main)
        self._build_search_entries(main)
        self._build_results(main)
        self._build_bottom_bar(main)

    def _build_dict_bar(self, parent):
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        frame.columnconfigure(1, weight=1)

        self.dict_button = ttk.Button(
            frame, text="Load Dictionary...", command=self._on_load_dict
        )
        self.dict_button.grid(row=0, column=0, padx=(0, 6))

        self.dict_label_var = tk.StringVar(value="No dictionary loaded")
        ttk.Label(frame, textvariable=self.dict_label_var).grid(
            row=0, column=1, sticky="w"
        )

    def _build_search_entries(self, parent):
        frame = ttk.Frame(parent)
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        frame.columnconfigure((1, 3), weight=1)

        ttk.Label(frame, text="Starts With:").grid(row=0, column=0, padx=(0, 4))
        self.start_var = tk.StringVar()
        start_entry = ttk.Entry(frame, textvariable=self.start_var, width=25)
        start_entry.grid(row=0, column=1, sticky="ew", padx=(0, 16))
        start_entry.bind("<KeyRelease>", self._on_key_release)

        ttk.Label(frame, text="Ends With:").grid(row=0, column=2, padx=(0, 4))
        self.end_var = tk.StringVar()
        end_entry = ttk.Entry(frame, textvariable=self.end_var, width=25)
        end_entry.grid(row=0, column=3, sticky="ew")
        end_entry.bind("<KeyRelease>", self._on_key_release)

    def _build_results(self, parent):
        frame = ttk.Frame(parent)
        frame.grid(row=2, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.results_listbox = tk.Listbox(
            frame, font=("Consolas", 10), activestyle="none",
            exportselection=False, selectmode=tk.EXTENDED
        )
        self.results_listbox.grid(row=0, column=0, sticky="nsew")
        self.results_listbox.bind("<Double-Button-1>", self._on_listbox_doubleclick)
        self.results_listbox.bind("<Button-3>", self._show_exception_menu)
        self.results_listbox.bind("<<ListboxSelect>>", self._on_exception_selection)

        scrollbar = ttk.Scrollbar(
            frame, orient="vertical", command=self.results_listbox.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.results_listbox.configure(yscrollcommand=scrollbar.set)

    def _build_bottom_bar(self, parent):
        frame = ttk.Frame(parent)
        frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        frame.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Load a dictionary to begin")
        ttk.Label(frame, textvariable=self.status_var).grid(
            row=0, column=0, sticky="w"
        )

        self.exc_count_var = tk.StringVar(value="Exceptions: 0")
        exc_label = ttk.Label(frame, textvariable=self.exc_count_var, cursor="hand2")
        exc_label.grid(row=0, column=1, padx=(8, 4))
        exc_label.bind("<Button-1>", lambda e: self._load_exceptions())

        self.add_exc_button = ttk.Button(
            frame, text="Add to Exceptions", state="disabled",
            command=self._add_selected_to_exceptions
        )
        self.add_exc_button.grid(row=0, column=2, padx=(0, 4))

        ttk.Button(frame, text="Clear", command=self._clear_results).grid(
            row=0, column=3, padx=(0, 0)
        )

    def _setup_protocols(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self._save_settings()
        self.root.destroy()

    def _on_load_dict(self):
        path = filedialog.askopenfilename(
            title="Select Dictionary File",
            filetypes=[
                ("Word lists", "*.txt *.json"),
                ("Text files", "*.txt"),
                ("JSON files", "*.json"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._load_dictionary(path)

    def _load_dictionary(self, path):
        self.status_var.set("Loading dictionary...")
        self.dict_button.config(state="disabled")
        self.results_listbox.delete(0, tk.END)
        self.start_var.set("")
        self.end_var.set("")
        t = threading.Thread(target=self._load_thread, args=(path,), daemon=True)
        t.start()

    def _load_thread(self, path):
        try:
            wordlist, from_cache = load_wordlist_from_dict(path)
            self.root.after(0, self._on_dict_loaded, path, wordlist, from_cache)
        except Exception as e:
            logger.exception("Failed to load dictionary")
            self.root.after(0, self._on_dict_error, str(e))

    def _on_dict_loaded(self, path, wordlist, from_cache):
        self.dict_path = path
        self.lookup.set_wordlist(wordlist)
        self.dict_label_var.set(f"Dict: {Path(path).name}")
        cache_hint = " (from cache)" if from_cache else ""
        self.status_var.set(f"{len(wordlist):,} words loaded{cache_hint}")
        self.dict_button.config(state="normal")
        self._save_settings()

    def _on_dict_error(self, error):
        messagebox.showerror(
            "Dictionary Error", f"Failed to load dictionary:\n\n{error}"
        )
        self.status_var.set("Error loading dictionary")
        self.dict_button.config(state="normal")

    def _on_key_release(self, event=None):
        if self._search_after_id:
            self.root.after_cancel(self._search_after_id)
        self._search_after_id = self.root.after(300, self._run_search)

    def _run_search(self):
        if not self.lookup.has_wordlist():
            return
        prefix = self.start_var.get().strip()
        suffix = self.end_var.get().strip()
        if not prefix and not suffix:
            self.results_listbox.delete(0, tk.END)
            self.status_var.set(
                f"{self.lookup.get_word_count():,} words available "
                "\u2014 type a prefix or suffix"
            )
            return
        self.status_var.set("Searching...")
        t = threading.Thread(
            target=self._search_thread, args=(prefix, suffix), daemon=True
        )
        t.start()

    def _search_thread(self, prefix, suffix):
        try:
            results, total = self.lookup.find_starting_and_ending_with(
                prefix, suffix, limit=self.RESULT_LIMIT
            )
            self.root.after(0, self._update_results, results, total)
        except Exception as e:
            logger.exception("Search failed")
            self.root.after(0, self._on_search_error, str(e))

    def _update_results(self, results, total):
        self.results_listbox.delete(0, tk.END)
        for i, word in enumerate(results):
            self.results_listbox.insert(tk.END, word)
            if word in self.exceptions:
                self.results_listbox.itemconfig(i, fg="gray")
        n = len(results)
        if n == 0:
            self.status_var.set("No words found")
        elif n < total:
            self.status_var.set(f"Showing {n:,} of {total:,} words")
        elif n == 1:
            self.status_var.set("1 word found")
        else:
            self.status_var.set(f"{n:,} words found")

    def _on_search_error(self, error):
        messagebox.showerror("Search Error", f"Search failed:\n\n{error}")

    def _clear_results(self):
        self.start_var.set("")
        self.end_var.set("")
        self.results_listbox.delete(0, tk.END)
        if self.lookup.has_wordlist():
            self.status_var.set(f"{self.lookup.get_word_count():,} words available")
        else:
            self.status_var.set("Load a dictionary to begin")

    def _load_exceptions(self):
        self.exceptions = _load_exc()
        self.exc_count_var.set(f"Exceptions: {len(self.exceptions)}")
        self._update_exception_colors()

    def _on_exception_selection(self, event=None):
        selection = self.results_listbox.curselection()
        self.add_exc_button.config(state="normal" if selection else "disabled")

    def _on_listbox_doubleclick(self, event):
        index = self.results_listbox.nearest(event.y)
        if index < 0 or index >= self.results_listbox.size():
            return
        word = self.results_listbox.get(index)
        self._add_exceptions_words([word])

    def _show_exception_menu(self, event):
        index = self.results_listbox.nearest(event.y)
        if index < 0 or index >= self.results_listbox.size():
            return
        word = self.results_listbox.get(index)
        menu = tk.Menu(self.root, tearoff=0)
        if word in self.exceptions:
            menu.add_command(
                label="Remove from Exceptions",
                command=lambda w=word: self._remove_exceptions_words([w])
            )
        else:
            menu.add_command(
                label="Add to Exceptions",
                command=lambda w=word: self._add_exceptions_words([w])
            )
        menu.tk_popup(event.x_root, event.y_root)

    def _add_selected_to_exceptions(self):
        selection = self.results_listbox.curselection()
        if not selection:
            return
        words = [self.results_listbox.get(i) for i in selection]
        self._add_exceptions_words(words)

    def _add_exceptions_words(self, words):
        before = len(self.exceptions)
        self.exceptions.update(w.lower() for w in words)
        added = len(self.exceptions) - before
        if added:
            _save_exc(sorted(self.exceptions))
            self._update_exception_ui()
            self._update_exception_colors()
            s = "s" if added != 1 else ""
            self.status_var.set(f"Added {added} word{s} to exceptions")
        else:
            self.status_var.set("Words already in exceptions")

    def _remove_exceptions_words(self, words):
        before = len(self.exceptions)
        for w in words:
            self.exceptions.discard(w.lower())
        removed = before - len(self.exceptions)
        if removed:
            _save_exc(sorted(self.exceptions))
            self._update_exception_ui()
            self._update_exception_colors()
            s = "s" if removed != 1 else ""
            self.status_var.set(f"Removed {removed} word{s} from exceptions")
        else:
            self.status_var.set("Words not in exceptions")

    def _update_exception_ui(self):
        self.exc_count_var.set(f"Exceptions: {len(self.exceptions)}")
        self._on_exception_selection()

    def _update_exception_colors(self):
        for i in range(self.results_listbox.size()):
            word = self.results_listbox.get(i)
            self.results_listbox.itemconfig(
                i, fg="gray" if word in self.exceptions else ""
            )

    def _load_settings(self):
        try:
            if SETTINGS_FILE.exists():
                data = json.loads(SETTINGS_FILE.read_text("utf-8"))
                self.dict_path = data.get("dict_path") or None
        except Exception:
            pass

    def _save_settings(self):
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {"dict_path": self.dict_path or ""}
            SETTINGS_FILE.write_text(json.dumps(data, indent=2), "utf-8")
        except Exception as e:
            logger.warning("Failed to save lookup settings: %s", e)


def main():
    try:
        root = tk.Tk()
        DictionaryLookupApp(root)
        root.mainloop()
    except Exception:
        import traceback
        error_msg = traceback.format_exc()
        logger.critical("Startup crash:\n%s", error_msg)
        try:
            tk.Tk().withdraw()
            messagebox.showerror("Startup Error", error_msg)
        except Exception:
            pass


if __name__ == "__main__":
    main()
