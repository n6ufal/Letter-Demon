import tkinter as tk
from tkinter import filedialog, messagebox
import json
import threading
import os
import pickle
import hashlib
import bisect
from typing import Dict, Optional, cast

# ── state ────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(BASE, ".dict_cache.pkl")
SETTINGS_PATH = os.path.join(BASE, ".dict_settings.json")
EXCEPTIONS_PATH = os.path.join(os.path.dirname(BASE), "exceptions.txt")

current_words = []
current_words_rev = []
current_exceptions = set()
last_loaded_path = None
exceptions_mtime = 0
_debounce_ids: Dict[str, Optional[str]] = {"starts": None, "ends": None}

# ── HiDPI ────────────────────────────────────────────────────────────────────
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

# ── cache ────────────────────────────────────────────────────────────────────
def get_file_hash(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def load_cache():
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, "rb") as f:
            return pickle.load(f)
    except Exception:
        return {}

def save_cache(cache):
    try:
        with open(CACHE_PATH, "wb") as f:
            pickle.dump(cache, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        pass

def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        return {}
    try:
        with open(SETTINGS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(settings):
    try:
        with open(SETTINGS_PATH, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass

def load_exceptions():
    global current_exceptions, exceptions_mtime
    if not os.path.exists(EXCEPTIONS_PATH):
        current_exceptions = set()
        exceptions_mtime = 0
        return
    
    try:
        mtime = os.path.getmtime(EXCEPTIONS_PATH)
        if mtime == exceptions_mtime:
            return  # No changes
        
        exceptions_mtime = mtime
        current_exceptions = set()
        
        with open(EXCEPTIONS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    current_exceptions.add(line.lower())
        
        status_var.set(f"Loaded {len(current_exceptions):,} exceptions")
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load exceptions: {str(e)}")

def save_exceptions():
    try:
        with open(EXCEPTIONS_PATH, "w", encoding="utf-8") as f:
            f.write("# Word exceptions - one per line\n")
            f.write("# Lines starting with # are comments\n")
            f.write("# These words will never be chosen by the macro\n")
            f.write("# Case-insensitive. Edit this file and click Reload Exceptions in the app\n\n")
            for word in sorted(current_exceptions):
                f.write(f"{word}\n")
        
        global exceptions_mtime
        exceptions_mtime = os.path.getmtime(EXCEPTIONS_PATH)
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save exceptions: {str(e)}")

def toggle_exception(word):
    word = word.lower().strip()
    if word in current_exceptions:
        current_exceptions.remove(word)
        status_var.set(f"Removed '{word}' from exceptions")
    else:
        current_exceptions.add(word)
        status_var.set(f"Added '{word}' to exceptions")
    
    save_exceptions()
    # Re-run current search to update display
    if sw_var.get(): run_search("starts")
    if ew_var.get(): run_search("ends")

# ── high-performance engine ──────────────────────────────────────────────────
def search_starts(words, query):
    if not words or not query: return []
    lo = bisect.bisect_left(words, query)
    hi = bisect.bisect_right(words, query + '\uffff')
    return words[lo:hi]

def search_ends(words_rev, query):
    if not words_rev or not query: return []
    rev_query = query[::-1]
    lo = bisect.bisect_left(words_rev, rev_query)
    hi = bisect.bisect_right(words_rev, rev_query + '\uffff')
    return sorted(w[::-1] for w in words_rev[lo:hi])

# ── load ──────────────────────────────────────────────────────────────────────
def load_dictionary(path=None):
    if path is None:
        path = filedialog.askopenfilename(filetypes=[("Dict files", "*.json *.txt")])
    if not path: return

    def _load():
        btn_load.config(state="disabled")
        status_var.set("Hashing file...")
        try:
            file_hash = get_file_hash(path)
            cache = load_cache()

            if file_hash in cache:
                entry = cache[file_hash]
                root.after(0, lambda: apply_dictionary(
                    entry["words"], entry["words_rev"], "from cache"
                ))
                return

            status_var.set("Parsing dictionary...")
            if path.endswith(".json"):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                raw = data if isinstance(data, list) else data.get("words", [])
                words = sorted(set(w.lower() for w in raw if isinstance(w, str)))
            else:
                with open(path, "r", encoding="utf-8") as f:
                    words = sorted(set(line.strip().lower() for line in f if line.strip()))

            words_rev = sorted(w[::-1] for w in words)

            cache[file_hash] = {"words": words, "words_rev": words_rev}
            save_cache(cache)
            
            settings = load_settings()
            settings["last_path"] = path
            settings["last_hash"] = file_hash
            save_settings(settings)

            root.after(0, lambda: apply_dictionary(
                words, words_rev, "cached"
            ))

        except Exception as e:
            root.after(0, lambda: messagebox.showerror("Error", str(e)))
            root.after(0, lambda: status_var.set("Load failed"))
        finally:
            root.after(0, lambda: btn_load.config(state="normal"))

    threading.Thread(target=_load, daemon=True).start()

def apply_dictionary(words, words_rev, source):
    global current_words, current_words_rev, last_loaded_path
    current_words = words
    current_words_rev = words_rev
    n = len(current_words)
    status_var.set(f"Loaded {n:,} words  [{source}]")
    toggle_search(True)
    if sw_var.get(): run_search("starts")
    if ew_var.get(): run_search("ends")

# ── search ────────────────────────────────────────────────────────────────────
def schedule_search(mode):
    if not current_words: return
    if _debounce_ids[mode] is not None:
        root.after_cancel(cast(str, _debounce_ids[mode]))
    _debounce_ids[mode] = root.after(150, lambda: run_search(mode))

def run_search(mode):
    _debounce_ids[mode] = None
    if not current_words: return

    query = (sw_var.get() if mode == "starts" else ew_var.get()).strip().lower()
    out_widget = out_starts if mode == "starts" else out_ends
    count_var = count_sw if mode == "starts" else count_ew

    if not query:
        out_widget.config(state="normal")
        out_widget.delete("1.0", "end")
        out_widget.config(state="disabled")
        count_var.set("")
        return

    results = (
        search_starts(current_words, query)
        if mode == "starts"
        else search_ends(current_words_rev, query)
    )

    count_var.set(f"{len(results):,} results")
    update_results(out_widget, results, query, mode)

def update_results(out_widget, results, query, mode):
    label = "starts with" if mode == "starts" else "ends with"

    out_widget.config(state="normal")
    out_widget.delete("1.0", "end")

    out_widget.insert("end", f"{len(results):,} words {label} '{query}'\n", "header")
    out_widget.insert("end", "─" * 32 + "\n", "dim")

    if results:
        col_width = 24
        cols = 3
        for i, word in enumerate(results):
            out_widget.insert("end", word.ljust(col_width))
            if (i + 1) % cols == 0:
                out_widget.insert("end", "\n")
        if len(results) % cols != 0:
            out_widget.insert("end", "\n")
    else:
        out_widget.insert("end", "\n  ✓ No matches — solid trap ending.\n", "good")

    out_widget.config(state="disabled")

# ── ui ────────────────────────────────────────────────────────────────────────
class CopyableText(tk.Text):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<Key>", self._handle_key)

    def _handle_key(self, event):
        if event.state & 0x4 and event.keysym.lower() in ('c', 'a'):
            return
        if event.keysym in ('Left', 'Right', 'Up', 'Down', 'Home', 'End'):
            return
        return "break"
class CopyableText(tk.Text):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<Key>", self._handle_key)

    def _handle_key(self, event):
        if event.state & 0x4 and event.keysym.lower() in ('c', 'a'):
            return
        if event.keysym in ('Left', 'Right', 'Up', 'Down', 'Home', 'End'):
            return
        return "break"

root = tk.Tk()
root.title("Dict Validator — Letter Demon")
root.configure(bg="#1a1a1a")
root.geometry("960x660")
root.minsize(560, 380)                       # ← allow small windows
root.resizable(True, True)

C_BG    = "#1a1a1a"
C_PANEL = "#242424"
C_ACCENT= "#00d084"
C_WARN  = "#ff9800"
C_TEXT  = "#e0e0e0"
C_DIM   = "#666666"
C_ENTRY = "#2e2e2e"
C_GOOD  = "#00d084"
C_WHITE = "#ffffff"

FONT_LABEL  = ("Consolas", 10)
FONT_BOLD   = ("Consolas", 10, "bold")
FONT_STATUS = ("Consolas", 9)
FONT_ENTRY  = ("Consolas", 12)
FONT_OUT    = ("Consolas", 11)
FONT_HEADER = ("Consolas", 11, "bold")

def styled_btn(parent, text, cmd, accent=False, color=C_ACCENT):
    return tk.Button(parent, text=text, command=cmd,
                     bg=color if accent else "#333",
                     fg="#000" if accent else C_TEXT,
                     relief="flat", font=FONT_LABEL,
                     padx=10, pady=4, cursor="hand2",
                     activebackground=color, activeforeground="#000")

def styled_entry(parent, var):
    e = tk.Entry(parent, textvariable=var, bg=C_ENTRY, fg=C_TEXT,
                 insertbackground=C_ACCENT, relief="flat",
                 font=FONT_ENTRY, width=12, state="disabled")
    e.bind("<FocusIn>",  lambda _: e.config(highlightthickness=1,
                                             highlightbackground=C_ACCENT,
                                             highlightcolor=C_ACCENT))
    e.bind("<FocusOut>", lambda _: e.config(highlightthickness=0))
    return e

search_entries = []
search_buttons = []

def toggle_search(enabled):
    state = "normal" if enabled else "disabled"
    for e in search_entries: e.config(state=state)
    for b in search_buttons: b.config(state=state)

# ── top bar
top = tk.Frame(root, bg=C_BG)
top.pack(fill="x", padx=10, pady=(10, 6))

btn_load = styled_btn(top, "⬆ Load", load_dictionary, accent=True, color=C_ACCENT)
btn_load.pack(side="left")

btn_exceptions = styled_btn(top, "🚫 Exceptions", load_exceptions, accent=False, color=C_WARN)
btn_exceptions.pack(side="left", padx=(6, 0))

status_var = tk.StringVar(value="No dictionary loaded")
tk.Label(top, textvariable=status_var, bg=C_BG, fg=C_DIM,
         font=FONT_STATUS).pack(side="left", padx=10)

def clear_cache():
    global current_words, current_words_rev, last_loaded_path
    if not os.path.exists(CACHE_PATH):
        messagebox.showinfo("Cache", "No cache found.")
        return
    try:
        os.remove(CACHE_PATH)
        current_words = []
        current_words_rev = []
        last_loaded_path = None
        settings = load_settings()
        settings.pop("last_path", None)
        settings.pop("last_hash", None)
        save_settings(settings)
        out_starts.config(state="normal"); out_starts.delete("1.0", "end"); out_starts.config(state="disabled")
        out_ends.config(state="normal"); out_ends.delete("1.0", "end"); out_ends.config(state="disabled")
        toggle_search(False)
        status_var.set("No dictionary loaded")
        messagebox.showinfo("Cache", "Cache cleared.")
    except Exception as e:
        messagebox.showerror("Error", str(e))

styled_btn(top, "Clear Cache", clear_cache, accent=False).pack(side="right")

tk.Frame(root, bg="#333", height=1).pack(fill="x", padx=10, pady=(2, 8))

# ── columns layout  —  grid instead of pack  ─────────────────────────────────
cols_frame = tk.Frame(root, bg=C_BG)
cols_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

cols_frame.columnconfigure(0, weight=1, minsize=200)
cols_frame.columnconfigure(1, weight=1, minsize=200)
cols_frame.rowconfigure(0, weight=1)

left_col  = tk.Frame(cols_frame, bg=C_BG)
left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

right_col = tk.Frame(cols_frame, bg=C_BG)
right_col.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

sw_var   = tk.StringVar()
ew_var   = tk.StringVar()
count_sw = tk.StringVar()
count_ew = tk.StringVar()

def make_column(parent, title, var, count_var, mode, accent_color):
    # Top Search Panel
    panel = tk.Frame(parent, bg=C_PANEL, padx=10, pady=10)
    panel.pack(fill="x")

    hrow = tk.Frame(panel, bg=C_PANEL)
    hrow.pack(fill="x", pady=(0, 6))
    tk.Label(hrow, text=title, bg=C_PANEL, fg=accent_color,
             font=FONT_BOLD).pack(side="left")
    tk.Label(hrow, textvariable=count_var, bg=C_PANEL,
             fg=accent_color, font=FONT_STATUS).pack(side="right")

    row = tk.Frame(panel, bg=C_PANEL)
    row.pack(fill="x")
    entry = styled_entry(row, var)
    entry.pack(side="left", fill="x", expand=True)
    entry.bind("<Return>", lambda _: run_search(mode))
    entry.bind("<Escape>", lambda _: var.set(""))

    btn = styled_btn(row, "Go", lambda: run_search(mode), accent=True, color=accent_color)
    btn.pack(side="left", padx=(6, 0))

    search_entries.append(entry)
    search_buttons.append(btn)

    var.trace_add("write", lambda *_: schedule_search(mode))

    # Bottom Results Panel
    out_frame = tk.Frame(parent, bg=C_BG)
    out_frame.pack(fill="both", expand=True, pady=(6, 0))

    scrollbar = tk.Scrollbar(out_frame, bg=C_PANEL, troughcolor=C_BG,
                             relief="flat", width=8)
    scrollbar.pack(side="right", fill="y")

    out = CopyableText(out_frame, bg=C_PANEL, fg=C_TEXT, font=FONT_OUT,
                       relief="flat", wrap="none",
                       yscrollcommand=scrollbar.set, padx=10, pady=8,
                       spacing1=2, spacing3=2)
    out.pack(fill="both", expand=True)
    scrollbar.config(command=out.yview)

    out.tag_config("header", foreground=C_WHITE, font=FONT_HEADER)
    out.tag_config("dim",    foreground=C_DIM)
    out.tag_config("good",   foreground=C_GOOD, font=("Consolas", 11, "bold"))

    return out

out_starts = make_column(left_col, "▶ STARTS WITH", sw_var, count_sw, "starts", C_ACCENT)
out_ends   = make_column(right_col, "◀ ENDS WITH", ew_var, count_ew, "ends", C_WARN)

# ── auto-load last dictionary on startup ──────────────────────────────────────
def auto_load_last_dictionary():
    settings = load_settings()
    last_path = settings.get("last_path")
    last_hash = settings.get("last_hash")
    
    if not last_path or not os.path.exists(last_path):
        return
    
    cache = load_cache()
    if last_hash not in cache:
        return
    
    entry = cache[last_hash]
    apply_dictionary(entry["words"], entry["words_rev"], "from cache (auto-loaded)")

root.after(100, auto_load_last_dictionary)

root.mainloop()
