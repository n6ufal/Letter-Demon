"""Logging bootstrap for the Lookup tool."""
import logging
from pathlib import Path


def setup_logging(project_root: str) -> None:
    log_dir = Path(project_root) / "data" / "runtime" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(str(log_dir / "lookup.log"), mode="a", encoding="utf-8"),
        ],
    )
