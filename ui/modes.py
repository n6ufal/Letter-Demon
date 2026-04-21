"""Mode / fallback labels — shared by main layout and settings persistence."""

MODE_DISPLAY = ["Trap", "Random", "Short", "Long"]
MODE_INTERNAL = ["Trap Words", "Random Words", "Short Words", "Long Words"]
FALLBACK_DISPLAY = ["Short", "Random", "Long"]
FALLBACK_INTERNAL = ["Short Words", "Random Words", "Long Words"]


def to_display_mode(internal: str) -> str:
    for d, i in zip(MODE_DISPLAY, MODE_INTERNAL):
        if i == internal:
            return d
    return MODE_DISPLAY[0]


def to_internal_mode(display: str) -> str:
    for d, i in zip(MODE_DISPLAY, MODE_INTERNAL):
        if d == display:
            return i
    return MODE_INTERNAL[0]


def to_display_fallback(internal: str) -> str:
    for d, i in zip(FALLBACK_DISPLAY, FALLBACK_INTERNAL):
        if i == internal:
            return d
    return FALLBACK_DISPLAY[0]


def to_internal_fallback(display: str) -> str:
    for d, i in zip(FALLBACK_DISPLAY, FALLBACK_INTERNAL):
        if d == display:
            return i
    return FALLBACK_INTERNAL[0]
