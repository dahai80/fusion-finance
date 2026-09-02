from __future__ import annotations

import csv
import io
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_DETECT_BYTES = 8192
_MAX_ROWS = 100000


def _sanitize_cell(val: str) -> str:
    if val and val.startswith(_CSV_FORMULA_PREFIXES):
        logger.warning("csv_loader: prefixing formula-like cell with single quote: %r", val[:32])
        return "'" + val
    return val


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
        try:
            csv.field_size_limit(min(131072, max(32768, 2 * 1024 * 1024)))
        except (ValueError, OverflowError) as e:
            logger.warning("csv_loader: cannot set field_size_limit (%s)", e)
        with open(path, encoding=enc, newline="") as f:
            delim = delimiter or self._detect_delimiter_stream(f)
            f.seek(0)
            reader = csv.reader(f, delimiter=delim)
            return self._consume_reader(reader, has_header, source_label=str(path))

    def _load_string(self, content: str, delimiter: str, has_header: bool) -> list[dict[str, Any]]:
        logger.info("Loading CSV from string (%d chars)", len(content))
        delim = delimiter or self._detect_delimiter(content)
        reader = csv.reader(io.StringIO(content), delimiter=delim)
        return self._consume_reader(reader, has_header, source_label="<string>")

    def _consume_reader(self, reader, has_header: bool, source_label: str) -> list[dict[str, Any]]:
        rows = []
        for row_count, row in enumerate(reader, 1):
            if row_count > _MAX_ROWS:
                logger.warning(
                    "csv_loader: row cap %d exceeded for %s; truncating remaining rows",
                    _MAX_ROWS,
                    source_label,
                )
                break
            rows.append(row)
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
        try:
            with open(path, "rb") as bf:
                raw = bf.read(_DETECT_BYTES)
        except OSError as e:
            logger.warning("csv_loader: cannot read %s for encoding detection (%s); defaulting utf-8", path, e)
            return "utf-8"
        for enc in self.ENCODINGS:
            try:
                raw.decode(enc)
                return enc
            except (UnicodeDecodeError, UnicodeError):
                continue
        return "utf-8"

    def _detect_delimiter_stream(self, f) -> str:
        sample = f.read(_DETECT_BYTES)
        first_line = sample.split("\n", 1)[0]
        f.seek(0)
        scores = {d: first_line.count(d) for d in self.DEFAULT_DELIMITERS}
        return max(scores, key=scores.get) if max(scores.values()) > 0 else ","

    def _detect_delimiter(self, content: str) -> str:
        first_line = content.split("\n")[0]
        scores = {d: first_line.count(d) for d in self.DEFAULT_DELIMITERS}
        return max(scores, key=scores.get) if max(scores.values()) > 0 else ","

    def _auto_type(self, val: str) -> Any:
        if not val:
            return None
        if val.startswith(_CSV_FORMULA_PREFIXES):
            return _sanitize_cell(val)
        try:
            return int(val)
        except ValueError:
            pass
        try:
            return float(val)
        except ValueError:
            pass
        return val
