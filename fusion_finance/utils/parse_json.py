from __future__ import annotations

import contextlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_MAX_PARSE_LEN = 256 * 1024
_HARD_CAP_LEN = 4 * 1024 * 1024


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


def _strip_fences(text: str) -> str:
    if "```json" in text:
        return text.split("```json")[1].split("```")[0].strip()
    if "```" in text:
        return text.split("```")[1].split("```")[0].strip()
    return text


def parse_json(text: Any) -> Any:
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    if not text:
        return None
    if len(text) > _HARD_CAP_LEN:
        logger.warning(
            "parse_json input too long (%d), exceeding hard cap %d, returning None", len(text), _HARD_CAP_LEN
        )
        return None
    if len(text) > _MAX_PARSE_LEN:
        logger.info("parse_json input large (%d), skipping full-load, using balanced extract", len(text))
        candidate = _strip_fences(text)
        obj = _extract_balanced(candidate, "{", "}")
        if obj:
            try:
                return json.loads(obj)
            except json.JSONDecodeError:
                pass
        arr = _extract_balanced(candidate, "[", "]")
        if arr:
            try:
                return json.loads(arr)
            except json.JSONDecodeError:
                pass
        logger.debug("parse_json failed for large text (len=%d)", len(text))
        return None
    candidate = _strip_fences(text)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    obj = _extract_balanced(candidate, "{", "}")
    if obj:
        try:
            parsed = json.loads(obj)
            remaining = candidate[candidate.find(obj) + len(obj) :].strip()
            if remaining and remaining[0] == "{":
                logger.warning("parse_json: multiple JSON objects detected, returning only the first")
            return parsed
        except json.JSONDecodeError:
            pass
    arr = _extract_balanced(candidate, "[", "]")
    if arr:
        try:
            return json.loads(arr)
        except json.JSONDecodeError:
            pass
    logger.debug("parse_json failed for text (len=%d)", len(text))
    return None


def extract_all_json(text: Any) -> list[Any]:
    if not text or not isinstance(text, str):
        return []
    text = text.strip()
    if not text:
        return []
    if len(text) > _HARD_CAP_LEN:
        logger.warning(
            "extract_all_json input too long (%d), exceeding hard cap %d, returning []", len(text), _HARD_CAP_LEN
        )
        return []
    candidate = _strip_fences(text)
    results: list[Any] = []
    cursor = 0
    while cursor < len(candidate):
        open_idx = candidate.find("{", cursor)
        if open_idx == -1:
            break
        obj = _extract_balanced(candidate[open_idx:], "{", "}")
        if obj is None:
            cursor = open_idx + 1
            continue
        with contextlib.suppress(json.JSONDecodeError):
            results.append(json.loads(obj))
        cursor = open_idx + len(obj)
    return results
