from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 11446
DEFAULT_MLX_BASE_URL = "http://localhost:11432/v1"
DEFAULT_MODEL = "qwen3.5-9b"

DATA_DIR = Path(os.getenv("FUSION_FINANCE_DATA_DIR", str(Path.home() / ".fusion" / "finance")))
AUDIT_DIR = DATA_DIR / "audit"
PROJECT_DIR = DATA_DIR / "projects"
CACHE_DIR = DATA_DIR / "cache"

LOG_LEVEL = os.getenv("FUSION_FINANCE_LOG_LEVEL", "INFO").upper()


def setup_logging(level: str = "") -> None:
    lvl = (level or LOG_LEVEL).upper()
    logging.basicConfig(
        level=getattr(logging, lvl, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("Fusion-Finance logging initialized, level=%s", lvl)


def ensure_dirs() -> None:
    for d in (DATA_DIR, AUDIT_DIR, PROJECT_DIR, CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)
    logger.debug("Data dirs ensured: %s", DATA_DIR)
