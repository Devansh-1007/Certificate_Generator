"""
Offline tests for the bulk pipeline's pure logic: roster parsing, column
mapping, and the anomaly agent. No DB, network, or API key required — mirrors
how the AI-designer agent is tested with a fake LLM.

Run: pytest test_bulk.py -v
"""

import io

import pytest

from bulk.parser import (
    parse_table,
    map_rows,
    detect_anomalies,
    suggest_rows,
    ParseError,
)


# ---------- parsing ----------

def test_parse_csv_basic():
    data = b"Name,Event\nAlice Smith,Hackathon\nBob Jones,Hackathon\n"
    rows = parse_table("roster.csv", data)
    assert rows == [
        {"Name": "Alice Smith", "Event": "Hackathon"},
        {"Name": "Bob Jones", "Event": "Hackathon"},
    ]


def test_parse_csv_skips_blank_rows_and_strips():
    data = b"Name,Event\n  Alice  , Hackathon \n\n,,\nBob,Expo\n"
    rows = parse_table("roster.csv", data)
    assert rows == [
        {"Name": "Alice", "Event": "Hackathon"},
        {"Name": "Bob", "Event": "Expo"},
    ]


def test_parse_strips_utf8_bom():
    data = "﻿Name,Event\nAlice,Expo\n".encode("utf-8")
    rows = parse_table("roster.csv", data)
    assert list(rows[0].keys())[0] == "Name"


def test_parse_tsv():
    data = b"Name\tEvent\nAlice\tExpo\n"
    rows = parse_table("roster.tsv", data)
    assert rows == [{"Name": "Alice", "Event": "Expo"}]


def test_parse_empty_file_raises():
    with pytest.raises(ParseError):
        parse_table("roster.csv", b"")


def test_parse_unsupported_type_raises():
    with pytest.raises(ParseError):
        parse_table("roster.pdf", b"whatever")


def test_parse_xlsx_roundtrip():
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Name", "Event"])
    ws.append(["Alice Smith", "Hackathon"])
    ws.append([None, None])  # blank row skipped
    ws.append(["Bob Jones", "Expo"])
    buf = io.BytesIO()
    wb.save(buf)
    rows = parse_table("roster.xlsx", buf.getvalue())
    assert rows == [
        {"Name": "Alice Smith", "Event": "Hackathon"},
        {"Name": "Bob Jones", "Event": "Expo"},
    ]


# ---------- column mapping ----------

<<<<<<< HEAD
def test_map_rows_alias_and_case_insensitive():
    rows = [{"full name": "Alice", "event name": "Expo"}]
    mapped, unmapped, report = map_rows(rows, ["RECIPIENT_NAME", "EVENT_NAME", "ISSUE_DATE"])
    # "full name" resolves via the synonym table; "event name" by normalized match
    assert mapped[0]["RECIPIENT_NAME"] == "Alice"
    assert mapped[0]["EVENT_NAME"] == "Expo"
    assert unmapped == ["ISSUE_DATE"]
    methods = {r["HEADER"]: r["METHOD"] for r in report}
    assert methods["full name"] == "alias" and methods["event name"] == "exact"
=======
def test_map_rows_case_insensitive():
    rows = [{"full name": "Alice", "event name": "Expo"}]
    mapped, unmapped = map_rows(rows, ["RECIPIENT_NAME", "EVENT_NAME", "ISSUE_DATE"])
    # "full name" doesn't normalize to RECIPIENT_NAME, but "event name" -> EVENT_NAME
    assert mapped[0]["EVENT_NAME"] == "Expo"
    assert "RECIPIENT_NAME" in unmapped
>>>>>>> 01e752bf247ce33f9427956dd13bdcf51af61e70


def test_map_rows_explicit_mapping():
    rows = [{"Student": "Alice", "Award": "Gold"}]
<<<<<<< HEAD
    mapped, unmapped, _report = map_rows(
=======
    mapped, unmapped = map_rows(
>>>>>>> 01e752bf247ce33f9427956dd13bdcf51af61e70
        rows, ["RECIPIENT_NAME", "EVENT_NAME"],
        mapping={"Student": "RECIPIENT_NAME", "Award": "EVENT_NAME"},
    )
    assert mapped[0] == {"RECIPIENT_NAME": "Alice", "EVENT_NAME": "Gold"}
    assert unmapped == []


def test_map_rows_normalized_header_match():
    rows = [{"Recipient_Name": "Alice"}]
<<<<<<< HEAD
    mapped, _unmapped, _report = map_rows(rows, ["RECIPIENT_NAME"])
=======
    mapped, _ = map_rows(rows, ["RECIPIENT_NAME"])
>>>>>>> 01e752bf247ce33f9427956dd13bdcf51af61e70
    assert mapped[0]["RECIPIENT_NAME"] == "Alice"


# ---------- anomaly agent ----------

def test_detects_missing_required():
    rows = [{"RECIPIENT_NAME": "Alice"}, {"RECIPIENT_NAME": ""}]
    report = detect_anomalies(rows, "RECIPIENT_NAME")
    missing = [a for a in report["anomalies"] if a["type"] == "missing"]
    assert len(missing) == 1
    assert missing[0]["row"] == 1


def test_detects_whitespace_and_suggests_trim():
    rows = [{"RECIPIENT_NAME": "Alice   Smith "}]
    report = detect_anomalies(rows, "RECIPIENT_NAME")
    ws = [a for a in report["anomalies"] if a["type"] == "whitespace"]
    assert ws and ws[0]["suggested"] == "Alice Smith"


def test_detects_casing_and_suggests_title():
    rows = [{"RECIPIENT_NAME": "ALICE SMITH"}, {"RECIPIENT_NAME": "bob jones"}]
    report = detect_anomalies(rows, "RECIPIENT_NAME")
    casing = {a["row"]: a["suggested"] for a in report["anomalies"] if a["type"] == "casing"}
    assert casing[0] == "Alice Smith"
    assert casing[1] == "Bob Jones"


def test_detects_exact_duplicate():
    rows = [{"RECIPIENT_NAME": "Alice Smith"}, {"RECIPIENT_NAME": "alice smith"}]
    report = detect_anomalies(rows, "RECIPIENT_NAME")
    dupes = [a for a in report["anomalies"] if a["type"] == "duplicate_exact"]
    assert len(dupes) == 1
    assert dupes[0]["duplicate_of"] == 0


def test_detects_near_duplicate():
    rows = [{"RECIPIENT_NAME": "Jonathan Smith"}, {"RECIPIENT_NAME": "Jonathon Smith"}]
    report = detect_anomalies(rows, "RECIPIENT_NAME")
    near = [a for a in report["anomalies"] if a["type"] == "duplicate_near"]
    assert len(near) == 1
    assert near[0]["duplicate_of"] == 0
    assert near[0]["score"] >= 88


def test_distinct_names_are_not_flagged_as_duplicates():
    rows = [{"RECIPIENT_NAME": "Alice Smith"}, {"RECIPIENT_NAME": "Priya Kapoor"}]
    report = detect_anomalies(rows, "RECIPIENT_NAME")
    assert not [a for a in report["anomalies"] if a["type"].startswith("duplicate")]


def test_report_counts_and_shape():
    rows = [{"RECIPIENT_NAME": "ALICE"}, {"RECIPIENT_NAME": ""}]
    report = detect_anomalies(rows, "RECIPIENT_NAME")
    assert report["total_rows"] == 2
    assert report["anomaly_count"] == len(report["anomalies"])
    assert report["counts"]["missing"] == 1


def test_suggest_rows_applies_safe_fixes_only():
    rows = [
        {"RECIPIENT_NAME": "ALICE  SMITH "},   # whitespace + casing -> fixed
        {"RECIPIENT_NAME": "Alice Smith"},     # exact dup, already clean -> untouched
    ]
    report = detect_anomalies(rows, "RECIPIENT_NAME")
    fixed = suggest_rows(rows, report)
    assert fixed[0]["RECIPIENT_NAME"] == "Alice Smith"
    # a duplicate is never auto-resolved — the row keeps its value for a human decision
    assert fixed[1]["RECIPIENT_NAME"] == "Alice Smith"
    assert any(a["type"] == "duplicate_exact" for a in report["anomalies"])
    # original untouched (suggest_rows returns a copy)
    assert rows[0]["RECIPIENT_NAME"] == "ALICE  SMITH "
<<<<<<< HEAD


# ---------- robust parsing (real-world roster shapes) ----------

def test_parses_semicolon_delimited_csv():
    """European Excel exports use ';' — the delimiter is sniffed, not assumed."""
    data = b"RECIPIENT_NAME;EVENT_NAME\nAlice Sharma;Expo\nRohan Mehta;Expo\n"
    rows = parse_table("roster.csv", data)
    assert len(rows) == 2 and rows[0]["RECIPIENT_NAME"] == "Alice Sharma"


def test_parses_pipe_delimited_csv():
    data = b"Name|Event\nAlice|Expo\n"
    rows = parse_table("roster.csv", data)
    assert rows[0]["Name"] == "Alice"


def test_skips_preamble_before_header():
    """Title/notes rows above the header must not be mistaken for columns."""
    data = b"Annual Hackathon 2026\n\nRECIPIENT_NAME,EVENT_NAME\nAlice,Expo\n"
    rows = parse_table("roster.csv", data)
    assert len(rows) == 1 and rows[0]["RECIPIENT_NAME"] == "Alice"


def test_duplicate_headers_are_disambiguated():
    data = b"Name,Name\nAlice,Bob\n"
    rows = parse_table("roster.csv", data)
    assert rows[0]["Name"] == "Alice" and rows[0]["Name_2"] == "Bob"


def test_rejects_oversized_file():
    from bulk.parser import MAX_UPLOAD_BYTES
    with pytest.raises(ParseError) as e:
        parse_table("roster.csv", b"x" * (MAX_UPLOAD_BYTES + 1))
    assert "larger than" in str(e.value)


def test_fuzzy_header_match_and_threshold():
    from bulk.parser import match_header
    ph = ["RECIPIENT_NAME", "EVENT_NAME"]
    target, score, how = match_header("Candidate Name", ph)
    assert target == "RECIPIENT_NAME" and how in ("alias", "fuzzy")
    # unrelated columns are left alone rather than force-mapped
    target, _score, how = match_header("Phone Number", ph)
    assert target is None and how == "none"


def test_one_placeholder_per_column():
    """Two columns matching the same placeholder: first wins, second flagged."""
    rows = [{"Name": "Alice", "Full Name": "Alice S"}]
    mapped, _unmapped, report = map_rows(rows, ["RECIPIENT_NAME"])
    assert mapped[0]["RECIPIENT_NAME"] == "Alice"
    assert any(r["METHOD"] == "duplicate_column" for r in report)
=======
>>>>>>> 01e752bf247ce33f9427956dd13bdcf51af61e70
