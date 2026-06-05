"""Mode / fallback labels — shared by main layout and settings persistence."""

_MODE_TO_INTERNAL = {
    "Trap": "Trap Words",
    "Random": "Random Words",
    "Short": "Short Words",
    "Long": "Long Words",
}
_MODE_TO_DISPLAY = {v: k for k, v in _MODE_TO_INTERNAL.items()}

_FALLBACK_TO_INTERNAL = {
    "Short": "Short Words",
    "Random": "Random Words",
    "Long": "Long Words",
}
_FALLBACK_TO_DISPLAY = {v: k for k, v in _FALLBACK_TO_INTERNAL.items()}

MODE_DISPLAY = tuple(_MODE_TO_INTERNAL.keys())
FALLBACK_DISPLAY = tuple(_FALLBACK_TO_INTERNAL.keys())


def to_display_mode(internal: str) -> str:
    return _MODE_TO_DISPLAY.get(internal, "Trap")


def to_internal_mode(display: str) -> str:
    return _MODE_TO_INTERNAL.get(display, "Trap Words")


def to_display_fallback(internal: str) -> str:
    return _FALLBACK_TO_DISPLAY.get(internal, "Short")


def to_internal_fallback(display: str) -> str:
    return _FALLBACK_TO_INTERNAL.get(display, "Short Words")
