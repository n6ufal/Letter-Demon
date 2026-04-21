"""Roblox process detection and window focus via WinAPI."""

import ctypes
import ctypes.wintypes


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_TH32CS_SNAPPROCESS = 0x00000002

# Set proper restype so INVALID_HANDLE_VALUE (-1) compares correctly
# on both 32-bit and 64-bit Windows.
_kernel32.CreateToolhelp32Snapshot.restype = ctypes.wintypes.HANDLE


class _PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize",              ctypes.wintypes.DWORD),
        ("cntUsage",            ctypes.wintypes.DWORD),
        ("th32ProcessID",       ctypes.wintypes.DWORD),
        ("th32DefaultHeapID",   ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID",        ctypes.wintypes.DWORD),
        ("cntThreads",          ctypes.wintypes.DWORD),
        ("th32ParentProcessID", ctypes.wintypes.DWORD),
        ("pcPriClassBase",      ctypes.c_long),
        ("dwFlags",             ctypes.wintypes.DWORD),
        ("szExeFile",           ctypes.c_char * 260),
    ]


def is_roblox_running() -> bool:
    """Check whether RobloxPlayerBeta.exe is in the process list."""
    INVALID = ctypes.wintypes.HANDLE(-1).value
    snapshot = _kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
    if ctypes.c_void_p(snapshot).value == INVALID:
        return False
    entry = _PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(_PROCESSENTRY32)
    found = False
    try:
        if _kernel32.Process32First(snapshot, ctypes.byref(entry)):
            while True:
                if entry.szExeFile == b"RobloxPlayerBeta.exe":
                    found = True
                    break
                if not _kernel32.Process32Next(snapshot, ctypes.byref(entry)):
                    break
    finally:
        _kernel32.CloseHandle(snapshot)
    return found


def focus_roblox_window() -> None:
    """Bring the Roblox window to the foreground (restore if minimized)."""
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        hwnd = user32.FindWindowW(None, "Roblox")
        if hwnd:
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


class RobloxMonitor:
    """Polls for the Roblox process and focuses its window."""

    def __init__(self, poll_interval_ms: int = 3000):
        self._poll_interval = poll_interval_ms
        self._running = False
        self._on_change = None  # callback(bool is_running)

    def start(self, on_change):
        """Begin polling. *on_change* is called with True/False on each tick."""
        self._on_change = on_change
        self._running = True
        self._poll()

    def stop(self):
        self._running = False

    def _poll(self):
        if not self._running:
            return
        running = is_roblox_running()
        if self._on_change:
            self._on_change(running)
        # Reschedule via the caller — the UI layer owns the after() call
