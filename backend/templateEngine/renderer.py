"""
Schema-driven certificate renderer.

Replaces hardcoded PIL coordinates: render_template() interprets any template
dict that passes validate_template(), substituting {PLACEHOLDER} tokens with
per-certificate data.
"""

import os
import re
import logging

from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(_BACKEND_DIR, "Templates", "Fonts")

FONT_FILES = {
    "arial": "arial.ttf",
    "lora-bold": "Lora-Bold.ttf",
}

_PLACEHOLDER_RE = re.compile(r"\{([A-Z0-9_]+)\}")
_font_cache = {}


def extract_placeholders(template):
    """Return the sorted set of {PLACEHOLDER} names used anywhere in the template."""
    found = set()
    for el in template.get("elements", []):
        for key in ("text", "data"):
            if key in el:
                found.update(_PLACEHOLDER_RE.findall(el[key]))
    return sorted(found)


def _substitute(value, data):
    def repl(m):
        name = m.group(1)
        if name not in data:
            raise KeyError("missing placeholder value: " + name)
        return str(data[name])

    return _PLACEHOLDER_RE.sub(repl, value)


def _font(name, size):
    key = (name, size)
    if key not in _font_cache:
        fname = FONT_FILES.get(name, FONT_FILES["arial"])
        _font_cache[key] = ImageFont.truetype(os.path.join(FONTS_DIR, fname), size)
    return _font_cache[key]


def _color(value, default=(0, 0, 0)):
    if value is None:
        return tuple(default)
    return tuple(value)


def _draw_text(draw, el, data, canvas_w):
    text = _substitute(el["text"], data)
    size = el["size"]
    fname = el.get("font", "arial")
    max_width = el.get("maxWidth")

    font = _font(fname, size)
    width = draw.textlength(text, font=font)

    # shrink-to-fit: long names must not bleed off the canvas
    while max_width and width > max_width and size > 10:
        size -= 2
        font = _font(fname, size)
        width = draw.textlength(text, font=font)

    align = el.get("align", "center")
    if align == "center":
        x = el.get("x", canvas_w // 2) - width / 2 if "x" in el else (canvas_w - width) / 2
    elif align == "right":
        x = el["x"] - width
    else:
        x = el["x"]

    draw.text((x, el["y"]), text, fill=_color(el.get("color")), font=font)


def _draw_qr(image, el, data):
    import qrcode

    payload = _substitute(el["data"], data)
    qr_img = qrcode.make(payload)
    qr_img = qr_img.resize((el["size"], el["size"]))
    image.paste(qr_img, (el["x"], el["y"]))


def render_template(template, data, assets_dir=None):
    """
    Render a validated template with `data` (placeholder name -> value).
    Returns a PIL RGB Image. Raises KeyError for missing placeholder values,
    OSError for missing image assets.
    """
    canvas = template["canvas"]
    w, h = canvas["width"], canvas["height"]

    if canvas.get("backgroundImage"):
        path = canvas["backgroundImage"]
        if assets_dir and not os.path.isabs(path):
            path = os.path.join(assets_dir, path)
        image = Image.open(path).convert("RGB").resize((w, h))
    else:
        image = Image.new("RGB", (w, h), _color(canvas.get("backgroundColor"), (255, 255, 255)))

    draw = ImageDraw.Draw(image)

    for el in template["elements"]:
        t = el["type"]
        if t == "text":
            _draw_text(draw, el, data, w)
        elif t == "rect":
            draw.rectangle(
                [el["x"], el["y"], el["x"] + el["width"], el["y"] + el["height"]],
                fill=_color(el.get("fill")) if el.get("fill") else None,
                outline=_color(el.get("outline")) if el.get("outline") else None,
                width=el.get("outlineWidth", 1),
            )
        elif t == "line":
            draw.line(
                [el["x1"], el["y1"], el["x2"], el["y2"]],
                fill=_color(el.get("color")),
                width=el.get("width", 2),
            )
        elif t == "image":
            path = el["path"]
            if assets_dir and not os.path.isabs(path):
                path = os.path.join(assets_dir, path)
            overlay = Image.open(path).convert("RGBA")
            if el.get("width") and el.get("height"):
                overlay = overlay.resize((el["width"], el["height"]))
            image.paste(overlay, (el["x"], el["y"]), overlay)
        elif t == "qr":
            _draw_qr(image, el, data)

    logging.info("Rendered template '%s' (%dx%d)", template.get("name"), w, h)
    return image


def layout_report(template):
    """
    Heuristic layout checks beyond schema validation: overlapping text boxes.
    Returns a list of warning strings (empty = clean). Used by the AI designer
    for self-correction and by the eval harness for scoring.
    """
    warnings = []
    boxes = []
    for i, el in enumerate(template["elements"]):
        if el["type"] != "text":
            continue
        est_w = el.get("maxWidth") or int(len(el["text"]) * el["size"] * 0.55)
        x = el.get("x", template["canvas"]["width"] // 2)
        if el.get("align", "center") == "center":
            x -= est_w // 2
        boxes.append((i, el.get("id", "text"), x, el["y"], x + est_w, el["y"] + el["size"]))

    for a in range(len(boxes)):
        for b in range(a + 1, len(boxes)):
            _, ida, ax1, ay1, ax2, ay2 = boxes[a]
            _, idb, bx1, by1, bx2, by2 = boxes[b]
            if ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2:
                warnings.append(
                    "text elements '{}' and '{}' likely overlap — adjust y positions".format(ida, idb)
                )
    return warnings
