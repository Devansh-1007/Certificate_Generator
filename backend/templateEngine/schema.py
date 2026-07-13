"""
Template JSON Schema — the contract between the renderer, the API, and the AI designer.

A template describes a canvas plus an ordered list of elements. Text values may
contain {PLACEHOLDERS} that are substituted with per-certificate data at render time.
"""

import logging

from jsonschema import Draft7Validator

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

FONTS = ["arial", "lora-bold"]  # maps to files in Templates/Fonts

COLOR = {
    "type": "array",
    "items": {"type": "integer", "minimum": 0, "maximum": 255},
    "minItems": 3,
    "maxItems": 4,
}

TEMPLATE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["name", "canvas", "elements"],
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 100},
        "description": {"type": "string"},
        "canvas": {
            "type": "object",
            "required": ["width", "height"],
            "additionalProperties": False,
            "properties": {
                "width": {"type": "integer", "minimum": 200, "maximum": 4000},
                "height": {"type": "integer", "minimum": 200, "maximum": 4000},
                "backgroundColor": COLOR,
                "backgroundImage": {"type": "string"},
            },
        },
        "elements": {
            "type": "array",
            "minItems": 1,
            "maxItems": 40,
            "items": {
                "type": "object",
                "required": ["type"],
                "properties": {
                    "id": {"type": "string"},
                    "type": {"enum": ["text", "rect", "line", "image", "qr"]},
                },
                "allOf": [
                    {
                        "if": {"properties": {"type": {"const": "text"}}},
                        "then": {
                            "required": ["text", "y", "size"],
                            "properties": {
                                "text": {"type": "string", "minLength": 1},
                                "x": {"type": "integer"},
                                "y": {"type": "integer"},
                                "size": {"type": "integer", "minimum": 8, "maximum": 400},
                                "font": {"enum": FONTS},
                                "color": COLOR,
                                "align": {"enum": ["left", "center", "right"]},
                                "maxWidth": {"type": "integer", "minimum": 20},
                                "letterSpacing": {"type": "integer", "minimum": 0, "maximum": 40},
                            },
                        },
                    },
                    {
                        "if": {"properties": {"type": {"const": "rect"}}},
                        "then": {
                            "required": ["x", "y", "width", "height"],
                            "properties": {
                                "x": {"type": "integer"},
                                "y": {"type": "integer"},
                                "width": {"type": "integer", "minimum": 1},
                                "height": {"type": "integer", "minimum": 1},
                                "fill": COLOR,
                                "outline": COLOR,
                                "outlineWidth": {"type": "integer", "minimum": 1, "maximum": 60},
                            },
                        },
                    },
                    {
                        "if": {"properties": {"type": {"const": "line"}}},
                        "then": {
                            "required": ["x1", "y1", "x2", "y2"],
                            "properties": {
                                "x1": {"type": "integer"},
                                "y1": {"type": "integer"},
                                "x2": {"type": "integer"},
                                "y2": {"type": "integer"},
                                "color": COLOR,
                                "width": {"type": "integer", "minimum": 1, "maximum": 40},
                            },
                        },
                    },
                    {
                        "if": {"properties": {"type": {"const": "image"}}},
                        "then": {
                            "required": ["path", "x", "y"],
                            "properties": {
                                "path": {"type": "string"},
                                "x": {"type": "integer"},
                                "y": {"type": "integer"},
                                "width": {"type": "integer", "minimum": 1},
                                "height": {"type": "integer", "minimum": 1},
                            },
                        },
                    },
                    {
                        "if": {"properties": {"type": {"const": "qr"}}},
                        "then": {
                            "required": ["data", "x", "y", "size"],
                            "properties": {
                                "data": {"type": "string", "minLength": 1},
                                "x": {"type": "integer"},
                                "y": {"type": "integer"},
                                "size": {"type": "integer", "minimum": 40, "maximum": 800},
                            },
                        },
                    },
                ],
            },
        },
    },
}

_validator = Draft7Validator(TEMPLATE_SCHEMA)


def validate_template(template):
    """
    Validate a template dict against TEMPLATE_SCHEMA plus semantic rules the
    schema language cannot express. Returns (ok: bool, errors: list[str]).
    Error strings are written to be actionable — they are fed back to the
    AI designer agent for self-correction.
    """
    errors = [
        "schema: {} (at {})".format(e.message, "/".join(str(p) for p in e.path))
        for e in _validator.iter_errors(template)
    ]
    if errors:
        return False, errors

    w = template["canvas"]["width"]
    h = template["canvas"]["height"]

    for i, el in enumerate(template["elements"]):
        tag = "element[{}] ({})".format(i, el.get("id", el["type"]))
        t = el["type"]
        if t == "text":
            y = el["y"]
            if not (0 <= y <= h - el["size"]):
                errors.append(
                    "{}: y={} with size={} overflows canvas height {} — keep y between 0 and {}".format(
                        tag, y, el["size"], h, h - el["size"]
                    )
                )
            if el.get("align", "center") != "center" and "x" not in el:
                errors.append("{}: align '{}' requires an explicit x".format(tag, el["align"]))
            if "x" in el and not (0 <= el["x"] < w):
                errors.append("{}: x={} outside canvas width {}".format(tag, el["x"], w))
        elif t == "rect":
            if el["x"] < 0 or el["y"] < 0 or el["x"] + el["width"] > w or el["y"] + el["height"] > h:
                errors.append("{}: rect exceeds canvas bounds ({}x{})".format(tag, w, h))
        elif t == "line":
            for k in ("x1", "x2"):
                if not (0 <= el[k] <= w):
                    errors.append("{}: {}={} outside canvas width {}".format(tag, k, el[k], w))
            for k in ("y1", "y2"):
                if not (0 <= el[k] <= h):
                    errors.append("{}: {}={} outside canvas height {}".format(tag, k, el[k], h))
        elif t in ("image", "qr"):
            ew = el.get("width", el.get("size", 0))
            eh = el.get("height", el.get("size", 0))
            if el["x"] < 0 or el["y"] < 0 or el["x"] + ew > w or el["y"] + eh > h:
                errors.append("{}: {} exceeds canvas bounds ({}x{})".format(tag, t, w, h))

    return (len(errors) == 0), errors
