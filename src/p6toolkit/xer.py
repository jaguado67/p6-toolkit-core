"""Lossless-enough read-only XER text parser; preserves all original field strings.

Supports %T/%F/%R/%E tables, tab delimiters and common export encodings.
No assumptions are made about Oracle's calendar binary/text payload.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import csv
import hashlib
import io


class XERParseError(ValueError):
    pass


@dataclass(frozen=True)
class XERTable:
    name: str
    fields: tuple[str, ...]
    rows: tuple[Mapping[str, str], ...]


@dataclass(frozen=True)
class XERDocument:
    filename: str
    sha256: str
    encoding: str
    header: tuple[str, ...]
    tables: Mapping[str, XERTable]
    warnings: tuple[str, ...]

    def rows(self, table_name: str) -> tuple[Mapping[str, str], ...]:
        table = self.tables.get(table_name.upper())
        return table.rows if table is not None else ()


def _decode(data: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise XERParseError("The XER file could not be decoded")


def parse_xer_bytes(data: bytes, filename: str = "upload.xer") -> XERDocument:
    if not data:
        raise XERParseError("The XER file is empty")
    text, encoding = _decode(data)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter="\t", quoting=csv.QUOTE_NONE)
    header: tuple[str, ...] = ()
    warnings: list[str] = []
    tables: dict[str, XERTable] = {}
    current_name: str | None = None
    current_fields: tuple[str, ...] = ()
    current_rows: list[dict[str, str]] = []
    ended = False

    def commit() -> None:
        nonlocal current_name, current_fields, current_rows
        if current_name is not None:
            if not current_fields:
                raise XERParseError(f"Table {current_name} has no %F header")
            tables[current_name] = XERTable(current_name, current_fields, tuple(current_rows))
        current_name, current_fields, current_rows = None, (), []

    for line_no, row in enumerate(reader, start=1):
        if not row or not any(cell.strip() for cell in row):
            continue
        marker = row[0].lstrip("\ufeff")
        if not header:
            if marker != "ERMHDR":
                raise XERParseError(f"Line {line_no}: missing ERMHDR header")
            header = tuple(row)
            continue
        if marker == "%T":
            if len(row) < 2 or not row[1].strip():
                raise XERParseError(f"Line {line_no}: missing table name")
            commit()
            current_name = row[1].strip().upper()
            if current_name in tables:
                raise XERParseError(f"Line {line_no}: duplicated table {current_name}")
        elif marker == "%F":
            if current_name is None or current_fields:
                raise XERParseError(f"Line {line_no}: unexpected %F")
            current_fields = tuple(row[1:])
            if not current_fields or len(current_fields) != len(set(current_fields)):
                raise XERParseError(f"Line {line_no}: empty or repeated fields")
        elif marker == "%R":
            if current_name is None or not current_fields:
                raise XERParseError(f"Line {line_no}: %R without table or fields")
            values = row[1:]
            if len(values) != len(current_fields):
                raise XERParseError(
                    f"Line {line_no}: {current_name} expects {len(current_fields)} fields; "
                    f"got {len(values)}"
                )
            current_rows.append(dict(zip(current_fields, values)))
        elif marker == "%E":
            commit()
            ended = True
            break
        else:
            raise XERParseError(f"Line {line_no}: unknown marker {marker!r}")

    if not header:
        raise XERParseError("Missing ERMHDR")
    if not ended:
        commit()
        warnings.append("XER without final %E marker")
    if not tables:
        raise XERParseError("XER without tables")
    if encoding == "latin-1":
        warnings.append("Fell back to Latin-1 encoding; check special characters")
    return XERDocument(filename, hashlib.sha256(data).hexdigest(), encoding,
                       header, tables, tuple(warnings))


def parse_xer_file(path: str | Path) -> XERDocument:
    path = Path(path)
    return parse_xer_bytes(path.read_bytes(), path.name)
