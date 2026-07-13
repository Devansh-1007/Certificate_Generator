"""
Tests for the template engine and the AI designer agent loop.
Run: pytest test_template_engine.py -v
The agent tests use a fake LLM — no API key or network needed.
"""

import os
import json
import copy

import pytest

from templateEngine.schema import validate_template
from templateEngine.renderer import render_template, extract_placeholders, layout_report
from aiDesigner.agent import design_template, MAX_ATTEMPTS

PRESET = os.path.join(os.path.dirname(__file__), "templateEngine", "presets", "default_certificate.json")


@pytest.fixture
def template():
    with open(PRESET) as f:
        return json.load(f)


@pytest.fixture
def data():
    return {
        "RECIPIENT_NAME": "Devansh Choudhary",
        "EVENT_NAME": "IIT BHU MUN 2023",
        "ISSUE_DATE": "12 July 2026",
        "SIGNATORY_NAME": "Dr. A. Sharma",
        "SIGNATORY_TITLE": "Director",
        "VERIFY_URL": "https://example.com/verify/abc123",
    }


# ---------- schema ----------

def test_default_template_is_valid(template):
    ok, errors = validate_template(template)
    assert ok, errors


def test_rejects_out_of_bounds_text(template):
    bad = copy.deepcopy(template)
    bad["elements"][2]["y"] = 5000
    ok, errors = validate_template(bad)
    assert not ok
    assert any("overflows" in e for e in errors)


def test_rejects_unknown_font(template):
    bad = copy.deepcopy(template)
    bad["elements"][2]["font"] = "comic-sans"
    ok, errors = validate_template(bad)
    assert not ok


def test_rejects_missing_canvas():
    ok, errors = validate_template({"name": "x", "elements": [{"type": "text", "text": "hi", "y": 0, "size": 12}]})
    assert not ok


# ---------- renderer ----------

def test_extract_placeholders(template):
    names = extract_placeholders(template)
    assert "RECIPIENT_NAME" in names and "VERIFY_URL" in names


def test_render_produces_correct_canvas(template, data):
    img = render_template(template, data)
    assert img.size == (1600, 1130)
    assert img.mode == "RGB"


def test_render_missing_placeholder_raises(template):
    with pytest.raises(KeyError):
        render_template(template, {"RECIPIENT_NAME": "X"})


def test_long_name_shrinks_not_overflows(template, data):
    data["RECIPIENT_NAME"] = "Dr. Maximiliana Wolfeschlegelsteinhausenbergerdorff-Rajagopalachari III"
    img = render_template(template, data)  # must not raise; maxWidth handles it
    assert img.size == (1600, 1130)


def test_layout_report_flags_overlap(template):
    bad = copy.deepcopy(template)
    bad["elements"][4]["y"] = bad["elements"][5]["y"]  # collide presented-to with recipient
    assert layout_report(bad)


# ---------- agent loop (fake LLM, no network) ----------

class FakeLLM:
    """Returns queued templates; lets us script bad-then-good sequences."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0
        self.last_messages = None

    def chat(self, messages, tool):
        self.calls += 1
        self.last_messages = messages
        return {"tool_input": self.outputs.pop(0), "text": ""}


def test_agent_accepts_valid_first_try(template):
    llm = FakeLLM([template])
    result = design_template("formal gold certificate", llm=llm)
    assert result["ok"] and result["attempts"] == 1


def test_agent_self_corrects(template):
    bad = copy.deepcopy(template)
    bad["elements"][2]["y"] = 5000
    llm = FakeLLM([bad, template])
    result = design_template("formal gold certificate", llm=llm)
    assert result["ok"] and result["attempts"] == 2
    # the retry prompt must contain the actionable error
    assert any("overflows" in m["content"] for m in llm.last_messages if m["role"] == "user")


def test_agent_gives_up_after_max_attempts(template):
    bad = copy.deepcopy(template)
    del bad["canvas"]
    llm = FakeLLM([bad] * MAX_ATTEMPTS)
    result = design_template("formal gold certificate", llm=llm)
    assert not result["ok"] and result["attempts"] == MAX_ATTEMPTS
