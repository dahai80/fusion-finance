from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_MAX_PARSE_LEN = 256 * 1024


def _extract_balanced(text: str, open_ch: str, close_ch: str) -> str | None:
    start = text.find(open_ch)
    while start != -1:
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        start = text.find(open_ch, start + 1)
    return None


def parse_json(text: Any) -> Any:
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    if not text:
        return None
    if len(text) > _MAX_PARSE_LEN:
        logger.warning("parse_json input too long (%d), truncating to %d", len(text), _MAX_PARSE_LEN)
        text = text[:_MAX_PARSE_LEN]
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    obj = _extract_balanced(text, "{", "}")
    if obj:
        try:
            return json.loads(obj)
        except json.JSONDecodeError:
            pass
    arr = _extract_balanced(text, "[", "]")
    if arr:
        try:
            return json.loads(arr)
        except json.JSONDecodeError:
            pass
    logger.debug("parse_json failed for text (len=%d)", len(text))
    return None
