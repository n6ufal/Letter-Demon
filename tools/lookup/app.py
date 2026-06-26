"""LookupApp — controller: owns DictLookup, exceptions, settings, search worker."""
import json
import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from config.exceptions import load_exceptions as _load_exc, save_exceptions as _save_exc
from config.trap_endings import TRAP_ENDINGS_FILE, load_trap_endings, save_trap_endings
from core import __version__
from core.dict_lookup import DictLookup
from core.dictionary import load_custom_words, load_wordlist_from_dict, save_custom_words
from ui.custom_words_dialog import CustomWordsDialog
from ui.file_editors import EditorDialog

from .view import LookupView
from .worker import SearchWorker

logger = logging.getLogger(__name__)

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
SETTINGS_FILE = Path(_PROJECT_ROOT) / "data" / "runtime" / "lookup_settings.json"

DEBOUNCE_MS = 300
FEEDBACK_MS_ERROR = 6000
FEEDBACK_MS_DICT_ERROR = 8000


class LookupApp:
    """Controller — owns DictLookup, exceptions, settings, and the search worker."""

    def __init__(self, root):
        self.root = root
        self.root.title(f"Dictionary Lookup v{__version__}")
        self.root.minsize(1100, 650)

        self.dict_path = None
        self.lookup = DictLookup()
        self.exceptions = set()
        self._search_after_id = None
        self._result_word_list = []
        self._settings = {}
        self.custom_words = load_custom_words()
        self._base_wordlist = None
        self.trap_endings = load_trap_endings()

        self._worker = SearchWorker(self.lookup)

        self.view = LookupView(root, self)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._load_settings()
        self._center_window()
        self._load_exceptions()
        self.refresh_trap_ui()

        if self.dict_path and Path(self.dict_path).is_file():
            self._load_dictionary(self.dict_path)

    def _center_window(self):
        self.root.update_idletasks()
        w = self._settings.get("win_w", 1400)
        h = self._settings.get("win_h", 800)
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------
    # Dictionary loading
    # ------------------------------------------------------------------

    def load_dict(self):
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
        self.view.set_status("Loading dictionary...")
        self.view.enable_dict_button(False)
        self.view.set_dict_empty()
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
        self._base_wordlist = wordlist
        if self.custom_words:
            wordlist = sorted(set(wordlist) | self.custom_words)
        self.lookup.set_wordlist(wordlist)
        self.view.set_dict_loaded(Path(path).name, len(wordlist))
        cache_hint = " (from cache)" if from_cache else ""
        extra = f" + {len(self.custom_words)} custom" if self.custom_words else ""
        self.view.set_status(f"{len(wordlist):,} words loaded{cache_hint}{extra}")
        self.view.enable_dict_button(True)
        self.view.enable_add_words_btn(True)

    def _on_dict_error(self, error):
        self.view.show_feedback("error",
                                f"Failed to load dictionary: {error}",
                                duration_ms=FEEDBACK_MS_DICT_ERROR)
        self.view.set_dict_empty()
        self.view.enable_dict_button(True)

    def add_words(self):
        if not self.lookup.has_wordlist():
            self.view.show_feedback("warn", "Load a dictionary first")
            return
        CustomWordsDialog(self.root, self)

    def remove_custom_words(self, words):
        before = len(self.custom_words)
        self.custom_words -= set(words)
        removed = before - len(self.custom_words)
        if not removed:
            self.view.set_status("Words not in custom words")
            return
        save_custom_words(self.custom_words)
        if self._base_wordlist is not None:
            merged = sorted(set(self._base_wordlist) | self.custom_words)
            self.lookup.set_wordlist(merged)
        self._run_search()
        s = "s" if removed != 1 else ""
        self.view.set_status(f"Removed {removed} custom word{s}")

    # ------------------------------------------------------------------
    # Trap Endings
    # ------------------------------------------------------------------

    def reload_trap_endings(self):
        self.trap_endings = load_trap_endings()
        self.refresh_trap_ui()
        self.view.set_status(f"Trap endings reloaded ({len(self.trap_endings)})")

    def refresh_trap_ui(self):
        self.view.update_trap_panel(self.trap_endings, self.view.trap_filter_text)
        self.view._trap_bottom_var.set(f"Trap Endings: {len(self.trap_endings)}")

    def add_trap_ending(self, ending):
        ending = ending.strip().lower()
        if not ending or not ending.isalpha():
            self.view.show_feedback("warn", "Ending must be alphabetic")
            return
        if ending in self.trap_endings:
            self.view.show_feedback("warn", f"'{ending}' already in trap endings")
            return
        self.trap_endings.append(ending)
        save_trap_endings(self.trap_endings)
        self.reload_trap_endings()
        self.view.set_status(f"Added '{ending}' to trap endings")

    def remove_trap_endings(self, endings):
        before = len(self.trap_endings)
        self.trap_endings = [e for e in self.trap_endings if e not in set(endings)]
        removed = before - len(self.trap_endings)
        if removed:
            save_trap_endings(self.trap_endings)
            self.reload_trap_endings()
            s = "s" if removed != 1 else ""
            self.view.set_status(f"Removed {removed} ending{s}")
        else:
            self.view.set_status("Endings not in list")

    def edit_trap_file(self):
        EditorDialog(
            self,
            title="Edit Trap Endings",
            file_path=TRAP_ENDINGS_FILE,
            reload_callback=self.reload_trap_endings,
            status_var=tk.StringVar(),
            default_content="# Trap endings - one per line, hardest first\n",
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_debounced(self, event=None):
        if self._search_after_id:
            self.root.after_cancel(self._search_after_id)
        self._search_after_id = self.root.after(DEBOUNCE_MS, self._run_search)

    def search_immediate(self):
        if self._search_after_id:
            self.root.after_cancel(self._search_after_id)
            self._search_after_id = None
        self._run_search()

    def _run_search(self):
        self._search_after_id = None
        if not self.lookup.has_wordlist():
            return
        prefix = self.view.prefix
        suffix = self.view.suffix
        if not prefix and not suffix:
            self.view.update_results([], 0, self.exceptions)
            self.view.set_status(
                f"{self.lookup.get_word_count():,} words available "
                "\u2014 type a prefix or suffix"
            )
            return
        self.view.set_status("Searching...")
        self._worker.submit(
            prefix, suffix, self.view.contains, self.view.min_len,
            self.view.max_len, self.view.match_case,
            on_result=lambda results, total: self.root.after(
                0, self._update_results, results, total),
            on_error=lambda error: self.root.after(0, self._on_search_error, error),
        )

    def _update_results(self, results, total):
        self._result_word_list = list(results)
        self.view.update_results(results, total, self.exceptions)
        n = len(results)
        if n == 0:
            self.view.set_status("No words found")
        else:
            self.view.set_status("Ready")

    def _on_search_error(self, error):
        self.view.show_feedback("error", f"Search failed: {error}",
                                duration_ms=FEEDBACK_MS_ERROR)

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def clear(self):
        self.view.reset_filters()
        self._result_word_list = []
        self.view.update_results([], 0, self.exceptions)
        if self.lookup.has_wordlist():
            self.view.set_status(f"{self.lookup.get_word_count():,} words available")
        else:
            self.view.set_status("Load a dictionary to begin")

    # ------------------------------------------------------------------
    # Query helpers (public interface for view, no direct attr access)
    # ------------------------------------------------------------------

    def get_result_word(self, index):
        return self._result_word_list[index]

    def is_exception(self, word):
        return word in self.exceptions

    def get_result_index(self, word):
        try:
            return self._result_word_list.index(word)
        except ValueError:
            return -1

    def get_setting(self, key, default=None):
        return self._settings.get(key, default)

    # ------------------------------------------------------------------
    # Exception management
    # ------------------------------------------------------------------

    def _load_exceptions(self):
        self.exceptions = _load_exc()
        self.refresh_exception_ui()

    def reload_exceptions(self):
        self._load_exceptions()
        self.view.set_status("Exceptions reloaded")

    def refresh_exception_ui(self):
        self.view.update_exception_panel(self.exceptions, self.view.exc_filter_text)
        self.view.set_exception_count_label(len(self.exceptions))
        self._refresh_result_colors()

    def refresh_exception_list(self):
        self.view.update_exception_panel(self.exceptions, self.view.exc_filter_text)

    def add_to_exceptions(self, words):
        before = len(self.exceptions)
        self.exceptions.update(w.lower() for w in words)
        added = len(self.exceptions) - before
        if added:
            _save_exc(sorted(self.exceptions))
            self.refresh_exception_ui()
            s = "s" if added != 1 else ""
            self.view.set_status(f"Added {added} word{s} to exceptions")
        else:
            self.view.set_status("Words already in exceptions")

    def remove_from_exceptions(self, words):
        before = len(self.exceptions)
        for w in words:
            self.exceptions.discard(w.lower())
        removed = before - len(self.exceptions)
        if removed:
            _save_exc(sorted(self.exceptions))
            self.refresh_exception_ui()
            s = "s" if removed != 1 else ""
            self.view.set_status(f"Removed {removed} word{s} from exceptions")
        else:
            self.view.set_status("Words not in exceptions")

    def add_selected(self):
        selection = self.view.results_listbox.curselection()
        if not selection:
            return
        words = [self.get_result_word(i) for i in selection]
        self.add_to_exceptions(words)

    def exception_click(self, word):
        found = self.view.scroll_to_word(word)
        if not found:
            self.view.set_status(
                f"'{word}' not in current results \u2014 try searching")

    def _refresh_result_colors(self):
        self.view.update_results(self._result_word_list,
                                 len(self._result_word_list), self.exceptions)

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _load_settings(self):
        try:
            if SETTINGS_FILE.exists():
                data = json.loads(SETTINGS_FILE.read_text("utf-8"))
                self._settings = data
                self.dict_path = data.get("dict_path") or None
        except Exception:
            self._settings = {}

    def _save_settings(self):
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "dict_path": self.dict_path or "",
                "win_w": self.root.winfo_width(),
                "win_h": self.root.winfo_height(),
            }
            try:
                data["sash_pos"] = self.view.paned.sashpos(0)
            except Exception:
                pass
            SETTINGS_FILE.write_text(json.dumps(data, indent=2), "utf-8")
        except Exception as e:
            logger.warning("Failed to save lookup settings: %s", e)

    def _on_close(self):
        self._save_settings()
        self.root.destroy()
