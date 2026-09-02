from __future__ import annotations

import json
import logging
import os
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_HOST = os.getenv("FUSION_FINANCE_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("FUSION_FINANCE_PORT", "11466"))
DEFAULT_MLX_BASE_URL = "http://localhost:11432/v1"
DEFAULT_MODEL = "qwen3.5-9b"

DATA_DIR = Path(os.getenv("FUSION_FINANCE_DATA_DIR", str(Path.home() / ".fusion" / "finance")))
AUDIT_DIR = DATA_DIR / "audit"
PROJECT_DIR = DATA_DIR / "projects"
CACHE_DIR = DATA_DIR / "cache"
EXPORT_DIR = DATA_DIR / "exports"

LOG_LEVEL = os.getenv("FUSION_FINANCE_LOG_LEVEL", "INFO").upper()

MAX_UPLOAD_BYTES = int(os.getenv("FUSION_FINANCE_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
MAX_LIST_LENGTH = int(os.getenv("FUSION_FINANCE_MAX_LIST_LENGTH", "10000"))
MAX_SIMULATIONS = int(os.getenv("FUSION_FINANCE_MAX_SIMULATIONS", "100000"))


def get_api_key() -> str:
    if os.getenv("FUSION_FINANCE_DISABLE_AUTH", "").lower() in ("1", "true", "yes"):
        logger.info("API auth disabled via FUSION_FINANCE_DISABLE_AUTH")
        return ""
    explicit = os.getenv("FUSION_FINANCE_API_KEY", "")
    if explicit:
        return explicit
    key_path = DATA_DIR / "api_key"
    try:
        if key_path.exists():
            stored = key_path.read_text(encoding="utf-8").strip()
            if stored:
                return stored
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        generated = secrets.token_urlsafe(32)
        key_path.write_text(generated, encoding="utf-8")
        try:
            os.chmod(key_path, 0o600)
        except OSError as e:
            logger.warning("chmod api_key failed: %s", e)
        logger.info("Generated new API key at %s", key_path)
        return generated
    except OSError as e:
        logger.error("Failed to init API key: %s", e)
        return ""


def get_cors_origins() -> list[str]:
    raw = os.getenv("FUSION_FINANCE_CORS_ORIGINS", "")
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return ["http://127.0.0.1", "http://localhost"]


def setup_logging(level: str = "") -> None:
    lvl = (level or LOG_LEVEL).upper()
    logging.basicConfig(
        level=getattr(logging, lvl, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("Fusion-Finance logging initialized, level=%s", lvl)


def ensure_dirs() -> None:
    for d in (DATA_DIR, AUDIT_DIR, PROJECT_DIR, CACHE_DIR, EXPORT_DIR):
        d.mkdir(parents=True, exist_ok=True)
    logger.debug("Data dirs ensured: %s", DATA_DIR)


def load_runtime_config() -> dict:
    return {
        "host": DEFAULT_HOST,
        "port": DEFAULT_PORT,
        "cors_origins": get_cors_origins(),
        "api_key_configured": bool(get_api_key()),
    }


def dump_runtime_config() -> str:
    return json.dumps(load_runtime_config(), ensure_ascii=False)
