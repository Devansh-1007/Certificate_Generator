"""
Roster parsing + the anomaly agent.

Everything here is pure (no Flask, DB, network or disk state) so it can be
unit-tested offline, mirroring how the AI-designer agent is tested with a fake
LLM. `rapidfuzz` (already a dependency) powers near-duplicate detection.

Flow:
    rows            = parse_table(filename, file_bytes)     # list[dict] keyed by header
    mapped, unmapped= map_rows(rows, placeholders, mapping) # header -> placeholder
    report          = detect_anomalies(mapped, name_field)  # findings + fixes
    cleaned         = suggest_rows(mapped, report)           # safe fixes pre-applied
"""

import io
import csv
import re

from rapidfuzz import fuzz

# A near-duplicate is flagged when two distinct names score at/above this.
NEAR_DUP_THRESHOLD = 88


class ParseError(Exception):
    """Raised when an uploaded file cannot be read as a table."""


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #

def parse_table(filename, file_bytes):
    """
    Parse an uploaded roster into a list of ordered dicts (header -> value).

    Supports .csv/.tsv (stdlib) and .xlsx (openpyxl, first sheet, row 1 = header).
    Blank rows are skipped. Raises ParseError on an unreadable or headerless file.
    """
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xlsm")):
        return _parse_xlsx(file_bytes)
    if name.endswith(".tsv"):
        return _parse_delimited(file_bytes, delimiter="\t")
    if name.endswith(".csv") or not name:
        return _parse_delimited(file_bytes, delimiter=",")
    raise ParseError(
        "Unsupported file type '{}'. Upload a .csv, .tsv or .xlsx file.".format(name)
    )


def _decode(file_bytes):
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ParseError("Could not decode the file — save it as UTF-8 and retry.")


def _parse_delimited(file_bytes, delimiter):
    text = _decode(file_bytes)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows_raw = [r for r in reader]
    if not rows_raw:
        raise ParseError("The file is empty.")

    headers = [h.strip() for h in rows_raw[0]]
    if not any(headers):
        raise ParseError("The first row must contain column headers.")

    rows = []
    for raw in rows_raw[1:]:
        if not any((c or "").strip() for c in raw):
            continue  # skip fully blank rows
        row = {}
        for i, header in enumerate(headers):
            if header:
                row[header] = (raw[i] if i < len(raw) else "").strip()
        rows.append(row)
    return rows


def _parse_xlsx(file_bytes):
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise ParseError(
            "Excel support needs openpyxl (`pip install openpyxl`). "
            "Alternatively upload the sheet as .csv."
        )
    try:
        wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as e:  # noqa: BLE001 - surface a clean message
        raise ParseError("Could not read the Excel file: {}".format(e))

    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        raise ParseError("The spreadsheet is empty.")

    headers = [("" if h is None else str(h)).strip() for h in header_row]
    if not any(headers):
        raise ParseError("The first row must contain column headers.")

    rows = []
    for raw in rows_iter:
        cells = ["" if c is None else str(c).strip() for c in raw]
        if not any(cells):
            continue
        row = {}
        for i, header in enumerate(headers):
            if header:
                row[header] = cells[i] if i < len(cells) else ""
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- #
# Column mapping (roster header -> template placeholder)
# --------------------------------------------------------------------------- #

def _norm_key(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def map_rows(rows, placeholders, mapping=None):
    """
    Re-key each row from roster headers to template placeholder names.

    `mapping` (optional) is an explicit {header: PLACEHOLDER} dict. Any header
    not in the mapping is auto-matched to a placeholder by normalized name
    (case/space/underscore-insensitive). Returns (mapped_rows, unmapped_placeholders).
    """
    mapping = mapping or {}
    placeholders = list(placeholders)
    norm_to_ph = {_norm_key(p): p for p in placeholders}
    explicit = {h: p for h, p in mapping.items()}

    mapped = []
    used = set()
    for row in rows:
        out = {}
        for header, value in row.items():
            target = explicit.get(header)
            if not target:
                target = norm_to_ph.get(_norm_key(header))
            if target:
                out[target] = value
                used.add(target)
        mapped.append(out)

    unmapped = [p for p in placeholders if p not in used]
    return mapped, unmapped


# --------------------------------------------------------------------------- #
# The anomaly agent
# --------------------------------------------------------------------------- #

def _clean_ws(value):
    return re.sub(r"\s+", " ", (value or "").strip())


def _title_case(value):
    # Title-case each word but keep short connectors lower except when first.
    small = {"of", "the", "and", "for", "de", "van", "da"}
    words = _clean_ws(value).split(" ")
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if i > 0 and lw in small:
            out.append(lw)
        else:
            out.append(lw[:1].upper() + lw[1:] if lw else lw)
    return " ".join(out)


def _finding(row, field, kind, severity, current, suggested, message, **extra):
    f = {
        "row": row,
        "field": field,
        "type": kind,
        "severity": severity,
        "current": current,
        "suggested": suggested,
        "message": message,
    }
    f.update(extra)
    return f


def detect_anomalies(rows, name_field, required_fields=None):
    """
    Inspect mapped rows and return a structured report of data-quality issues
    with proposed fixes, for a human to approve (maker-checker).

    Detects:
      * missing        — a required field is blank (needs a human; no auto-fix)
      * whitespace     — leading/trailing/double spaces (safe auto-fix: trim)
      * casing         — ALL CAPS / all lower name (auto-fix: Title Case)
      * duplicate_exact— identical name in an earlier row (needs a human)
      * duplicate_near — fuzzily similar name in an earlier row (needs review)

    `name_field` is the placeholder used as the certificate's unique name.
    """
    required = list(required_fields) if required_fields else [name_field]
    anomalies = []
    seen = {}  # normalized name -> first row index

    for i, row in enumerate(rows):
        # missing required fields
        for field in required:
            if not (row.get(field) or "").strip():
                anomalies.append(_finding(
                    i, field, "missing", "high",
                    row.get(field, ""), None,
                    "Required field '{}' is empty.".format(field),
                ))

        name = row.get(name_field, "") or ""
        if not name.strip():
            continue

        # whitespace hygiene on the name field
        cleaned = _clean_ws(name)
        if cleaned != name:
            anomalies.append(_finding(
                i, name_field, "whitespace", "low",
                name, cleaned,
                "Extra whitespace — trim to '{}'.".format(cleaned),
            ))

        # casing on the name field
        if cleaned and (cleaned.isupper() or cleaned.islower()):
            titled = _title_case(cleaned)
            if titled != cleaned:
                anomalies.append(_finding(
                    i, name_field, "casing", "medium",
                    cleaned, titled,
                    "Inconsistent casing — suggest '{}'.".format(titled),
                ))

        # duplicate detection against earlier rows
        key = _clean_ws(name).lower()
        if key in seen:
            anomalies.append(_finding(
                i, name_field, "duplicate_exact", "high",
                cleaned, None,
                "Duplicate of row {} — will overwrite unless renamed.".format(seen[key] + 1),
                duplicate_of=seen[key],
            ))
        else:
            near = _nearest(key, seen)
            if near is not None:
                other_idx, score = near
                anomalies.append(_finding(
                    i, name_field, "duplicate_near", "medium",
                    cleaned, None,
                    "Looks similar to row {} ('{}', {}% match) — possible typo.".format(
                        other_idx + 1, rows[other_idx].get(name_field, ""), int(score)
                    ),
                    duplicate_of=other_idx, score=int(score),
                ))
            seen[key] = i

    counts = {}
    for a in anomalies:
        counts[a["type"]] = counts.get(a["type"], 0) + 1

    return {
        "total_rows": len(rows),
        "anomaly_count": len(anomalies),
        "counts": counts,
        "anomalies": anomalies,
    }


def _nearest(key, seen):
    """Return (row_index, score) of the closest earlier name at/above threshold."""
    best_idx, best_score = None, 0
    for other_key, idx in seen.items():
        score = fuzz.ratio(key, other_key)
        if score >= NEAR_DUP_THRESHOLD and score > best_score:
            best_idx, best_score = idx, score
    return (best_idx, best_score) if best_idx is not None else None


def suggest_rows(rows, report):
    """
    Return a deep copy of `rows` with the SAFE auto-fixes (whitespace, casing)
    from the report applied, so the UI can preview a cleaned roster. Duplicates
    and missing values are left untouched — those need a human decision.
    """
    fixed = [dict(r) for r in rows]
    for a in report.get("anomalies", []):
        if a["type"] in ("whitespace", "casing") and a["suggested"] is not None:
            fixed[a["row"]][a["field"]] = a["suggested"]
    return fixed
