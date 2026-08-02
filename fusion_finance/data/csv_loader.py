from __future__ import annotations

import csv
import io
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CSVLoader:
    ENCODINGS = ["utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"]
    DEFAULT_DELIMITERS = [",", "\t", ";", "|"]

    def load(
        self, source: str | Path, delimiter: str = "", encoding: str = "", has_header: bool = True
    ) -> list[dict[str, Any]]:
        if isinstance(source, Path):
            return self._load_file(source, delimiter, encoding, has_header)
        if isinstance(source, str) and source.strip() and "\n" not in source and len(source) < 260:
            path = Path(source)
            if path.is_file():
                return self._load_file(path, delimiter, encoding, has_header)
        return self._load_string(str(source), delimiter, has_header)

    def _load_file(self, path: Path, delimiter: str, encoding: str, has_header: bool) -> list[dict[str, Any]]:
        enc = encoding or self._detect_encoding(path)
        logger.info("Loading CSV file: %s (encoding=%s)", path, enc)
        with open(path, encoding=enc) as f:
            content = f.read()
        return self._parse(content, delimiter, has_header)

    def _load_string(self, content: str, delimiter: str, has_header: bool) -> list[dict[str, Any]]:
        logger.info("Loading CSV from string (%d chars)", len(content))
        return self._parse(content, delimiter, has_header)

    def _parse(self, content: str, delimiter: str, has_header: bool) -> list[dict[str, Any]]:
        delim = delimiter or self._detect_delimiter(content)
        reader = csv.reader(io.StringIO(content), delimiter=delim)
        rows = list(reader)
        if not rows:
            return []
        if has_header:
            headers = [h.strip() for h in rows[0]]
            data = []
            for row in rows[1:]:
                if not any(cell.strip() for cell in row):
                    continue
                record = {}
                for i, header in enumerate(headers):
                    val = row[i].strip() if i < len(row) else ""
                    record[header] = self._auto_type(val)
                data.append(record)
            return data
        return [
            {f"col_{i}": self._auto_type(cell.strip()) for i, cell in enumerate(row)}
            for row in rows
            if any(c.strip() for c in row)
        ]

    def _detect_encoding(self, path: Path) -> str:
        for enc in self.ENCODINGS:
            try:
                path.read_text(encoding=enc)
                return enc
            except (UnicodeDecodeError, UnicodeError):
                continue
        return "utf-8"

    def _detect_delimiter(self, content: str) -> str:
        first_line = content.split("\n")[0]
        scores = {d: first_line.count(d) for d in self.DEFAULT_DELIMITERS}
        return max(scores, key=scores.get) if max(scores.values()) > 0 else ","

    def _auto_type(self, val: str) -> Any:
        if not val:
            return None
        try:
            return int(val)
        except ValueError:
            pass
        try:
            return float(val)
        except ValueError:
            pass
        return val
