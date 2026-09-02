from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def sanitize_name(name: str, fallback: str = "untitled") -> str:
    if not name:
        return fallback
    cleaned = Path(name).name
    cleaned = cleaned.strip()
    if not cleaned or cleaned in (".", ".."):
        return fallback
    if not _SAFE_NAME_RE.match(cleaned):
        cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", cleaned)
    if not cleaned:
        return fallback
    return cleaned


def safe_join(base: Path, *parts: str, suffix: str = "") -> Path | None:
    base_resolved = base.resolve()
    candidates = [str(Path(p).name) for p in parts if p]
    if not candidates:
        return None
    target = base_resolved.joinpath(*candidates)
    if suffix:
        target = target.with_suffix(suffix)
    target = target.resolve()
    try:
        target.relative_to(base_resolved)
    except ValueError:
        logger.warning("path traversal blocked: base=%s target=%s", base_resolved, target)
        return None
    return target
