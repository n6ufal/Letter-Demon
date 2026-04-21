"""Trap endings — load/save trap_endings.txt."""

import os

from .settings import get_project_root

TRAP_ENDINGS_FILE = os.path.join(get_project_root(), "trap_endings.txt")

DEFAULT_TRAP_ENDINGS = [
    # 1-letter — hardest single letters to respond to
    "x", "z", "q",
    # 2-letter — very difficult endings
    "nk", "xt", "xh", "wk", "wr", "nx", "rz", "zh", "mn",
    "zw", "gv", "fv", "bn", "nm", "hm",
    # 3-letter — tough endings
    "ism", "ugh", "nth", "nks", "mps", "lth", "rth",
    "zzy", "xus", "nux", "vex", "wux", "jks", "cks",
    "nds", "lps", "rps", "nts", "rks", "lks", "ngs",
    # 4-letter — moderately difficult
    "ness", "tion", "ight", "ough", "ment", "ence",
    "ance", "ings", "tion", "sion", "ping", "ring",
    "ling", "ding", "ting", "ming", "sing", "king",
    "bing", "ning", "ving", "wing", "zing",
    "dock", "lock", "rock", "sock", "mock", "flock",
    "tuck", "luck", "duck", "buck", "ruck",
    "dusk", "musk", "bask", "cask",
    "jump", "bump", "lump", "pump", "dump", "rump",
    "hunt", "punt", "bunt", "runt", "stunt",
    "gift", "lift", "drift", "shift", "sift", "tuft",
    "raft", "craft", "draft", "shaft",
    "depth", "length", "strength", "breadth", "width",
    "myth", "lymph", "synth", "nymph",
    "lynx", "phalanx", "appendix",
    # 5-letter — medium difficulty
    "ments", "tinge", "ought", "aught",
    "oughts", "aughts", "eights", "ights",
    "thing", "think", "thank", "thunk",
    "runch", "crunch", "grunch",
    "world", "would", "could", "should",
    # Multi-letter — situational traps
    "que", "gue", "ique", "esque",
    "psy", "phy", "logy", "graphy",
    "ology", "ography", "ography",
    "tzsch", "witz", "schw",
    "ngwi", "ndwi", "mbwi",
    "xism", "zism", "qat", "qis",
    "fy", "gy", "my", "by", "cy",
    "ve", "ze", "ge", "fe",
    "scape", "scope",
    "tique", "nique",
    "chr", "phr", "shr",
    "nth", "sch",
    "dge", "tch",
    "ogn", "ign",
    "ode", "ade", "ude",
    "oft", "eft", "aft",
    "omb", "amp", "ump",
    "isk", "esk", "osk",
    "eon", "ion", "eon",
    "ase", "ose", "use",
    "ine", "one", "une",
    "ire", "ore", "ure",
    "ial", "ual", "eal",
    "ic", "ac", "uc",
]


def load_trap_endings() -> list[str]:
    try:
        with open(TRAP_ENDINGS_FILE, "r") as f:
            endings = [line.strip().lower() for line in f if line.strip() and not line.startswith("#")]
        if endings:
            return list(dict.fromkeys(endings))  # deduplicate, preserve order
    except Exception:
        pass
    save_trap_endings(DEFAULT_TRAP_ENDINGS)
    return DEFAULT_TRAP_ENDINGS


def save_trap_endings(endings: list[str]) -> None:
    try:
        with open(TRAP_ENDINGS_FILE, "w") as f:
            f.write("# Trap endings - one per line, hardest first\n")
            f.write("# Lines starting with # are comments\n")
            f.write("# Edit this file and click Reload Traps in the app\n\n")
            for e in endings:
                f.write(e + "\n")
    except Exception as ex:
        print("Failed to save trap endings:", ex)
