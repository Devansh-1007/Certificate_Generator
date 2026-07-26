"""
The template-designer agent: a hand-rolled tool-calling loop with self-correction.

design_template(prompt) asks the LLM to emit a template via the emit_template
tool, then validates it three ways — JSON Schema, semantic bounds checks, and a
real test render — and feeds every failure back to the model for another
attempt. Returns the final template plus a full trace for debugging/evals.
"""

import json
import logging

from templateEngine.schema import TEMPLATE_SCHEMA, validate_template
from templateEngine.renderer import render_template, layout_report, extract_placeholders
from aiDesigner.llm import LLMClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

MAX_ATTEMPTS = 3

EMIT_TEMPLATE_TOOL = {
    "name": "emit_template",
    "description": "Emit the certificate template as JSON conforming to the template schema.",
    "input_schema": TEMPLATE_SCHEMA,
}

SYSTEM_PROMPT = """You are a senior certificate designer for a certificate generation platform.
You convert a plain-English description into a template JSON emitted through the emit_template tool.
Even a lazy one-line request must produce an elegant, print-worthy certificate.

HARD LAYOUT RULES (violations are rejected):
- Canvas: landscape 1600x1130 unless the user asks otherwise.
- NEVER set "x" on centered text — omit x and it centers on the canvas. Only use x with align left/right.
- Every text containing a {PLACEHOLDER} must set maxWidth (<= 1300 on a 1600 canvas).
- Keep >= 50px vertical gap between text baselines; nothing within 60px of the canvas edge except borders.
- {RECIPIENT_NAME} is required and must be the largest text (size 84-100, lora-bold).

DESIGN RECIPE (follow unless the user asks otherwise):
1. Background: soft off-white tint (e.g. [253,251,247]) or a pale tint of the requested theme color.
2. Double border: outer rect outline 6px at 40px inset, inner rect outline 2px at 60px inset, in the accent color.
3. Title (e.g. "CERTIFICATE"): lora-bold ~96, dark neutral [45,45,45], y~150.
4. Subtitle ("OF ACHIEVEMENT" etc.): lora-bold ~40 in the accent color, y~265.
5. Lead-in line ("This certificate is proudly presented to"): arial ~32, gray [90,90,90], y~400.
6. {RECIPIENT_NAME}: lora-bold ~92, y~470, maxWidth 1300, with a decorative line under it (x1 400 to x2 1200).
7. Reason line mentioning {EVENT_NAME}: arial ~34, y~650, maxWidth 1300.
8. "Awarded on {ISSUE_DATE}": arial ~28, y~760.
9. Signature: line from 1050 to 1400 at y~950, then "{SIGNATORY_NAME}, {SIGNATORY_TITLE}" arial 24 centered at x 1225, y~965, maxWidth 340.
10. If verification/QR is wanted: qr with data "{VERIFY_URL}", size 160, bottom-left (x 120, y 870).

Accent palette by mood: formal = gold [176,141,87]; corporate = navy [30,58,95]; nature/eco = deep green [32,74,50]; playful = coral [224,88,66]. Derive others sensibly from the request.

EXAMPLE (formal gold, abbreviated — match this structure and spacing):
{"name":"Classic Achievement","canvas":{"width":1600,"height":1130,"backgroundColor":[253,251,247]},
 "elements":[
  {"type":"rect","x":40,"y":40,"width":1520,"height":1050,"outline":[176,141,87],"outlineWidth":6},
  {"type":"rect","x":60,"y":60,"width":1480,"height":1010,"outline":[176,141,87],"outlineWidth":2},
  {"type":"text","text":"CERTIFICATE","y":150,"size":96,"font":"lora-bold","color":[45,45,45],"align":"center"},
  {"type":"text","text":"OF ACHIEVEMENT","y":265,"size":40,"font":"lora-bold","color":[176,141,87],"align":"center"},
  {"type":"text","text":"This certificate is proudly presented to","y":400,"size":32,"font":"arial","color":[90,90,90],"align":"center"},
  {"type":"text","text":"{RECIPIENT_NAME}","y":470,"size":92,"font":"lora-bold","color":[45,45,45],"align":"center","maxWidth":1300},
  {"type":"line","x1":400,"y1":600,"x2":1200,"y2":600,"color":[176,141,87],"width":3},
  {"type":"text","text":"for outstanding performance in {EVENT_NAME}","y":650,"size":34,"font":"arial","color":[90,90,90],"align":"center","maxWidth":1300},
  {"type":"text","text":"Awarded on {ISSUE_DATE}","y":760,"size":28,"font":"arial","color":[90,90,90],"align":"center","maxWidth":800},
  {"type":"line","x1":1050,"y1":950,"x2":1400,"y2":950,"color":[90,90,90],"width":2},
  {"type":"text","text":"{SIGNATORY_NAME}, {SIGNATORY_TITLE}","x":1225,"y":965,"size":24,"font":"arial","color":[90,90,90],"align":"center","maxWidth":340}]}

If you receive validation errors, fix exactly those problems and emit the full corrected template again."""


def _sample_data(template):
    """Fabricate plausible values for every placeholder so a test render can run."""
    samples = {
        "RECIPIENT_NAME": "Alexandra Rodriguez-Whitworth",  # long on purpose
        "EVENT_NAME": "Annual Innovation Challenge 2026",
        "ISSUE_DATE": "12 July 2026",
        "SIGNATORY_NAME": "Dr. A. Sharma",
        "SIGNATORY_TITLE": "Director",
        "VERIFY_URL": "https://example.com/verify/abc123",
    }
    return {name: samples.get(name, "Sample " + name.title()) for name in extract_placeholders(template)}


def design_template(prompt, llm=None):
    """
    Returns {"ok": bool, "template": dict|None, "attempts": int, "trace": list}.
    trace records every attempt: the errors found and whether the render passed.
    """
    llm = llm or LLMClient()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Design this certificate template: " + prompt},
    ]
    trace = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        result = llm.chat(messages, EMIT_TEMPLATE_TOOL)
        template = result["tool_input"]

        if template is None:
            errors = ["no emit_template tool call in response — you must call the tool"]
        else:
            ok, errors = validate_template(template)
            if ok:
                errors = list(layout_report(template))
                if "{RECIPIENT_NAME}" not in json.dumps(template):
                    errors.append("template must include the {RECIPIENT_NAME} placeholder")
                if not errors:
                    try:
                        render_template(template, _sample_data(template))
                    except Exception as e:
                        errors = ["test render failed: " + str(e)]

        trace.append({"attempt": attempt, "errors": errors})

        if not errors:
            logging.info("Template designed in %d attempt(s): '%s'", attempt, template.get("name"))
            return {"ok": True, "template": template, "attempts": attempt, "trace": trace}

        logging.info("Attempt %d failed validation: %s", attempt, errors)
        messages.append({"role": "assistant", "content": "emit_template call:\n" + json.dumps(template)})
        messages.append({
            "role": "user",
            "content": "That template failed validation:\n- "
            + "\n- ".join(errors)
            + "\nEmit the full corrected template via emit_template.",
        })

    return {"ok": False, "template": None, "attempts": MAX_ATTEMPTS, "trace": trace}
