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

SYSTEM_PROMPT = """You are a certificate template designer for a certificate generation platform.
You convert a plain-English description into a template JSON emitted through the emit_template tool.

Design rules:
- Canvas: landscape certificates are typically 1600x1130; portrait 1130x1600. Use these unless the user asks otherwise.
- Fonts available: "lora-bold" (serif, for titles and recipient names) and "arial" (for body text).
- Use {PLACEHOLDERS} in UPPER_SNAKE_CASE for dynamic values: {RECIPIENT_NAME} is required in every design;
  use {EVENT_NAME}, {ISSUE_DATE}, {SIGNATORY_NAME}, {VERIFY_URL} and others where they fit the request.
- The recipient name element should be the visual focus (size 80-100) and must have maxWidth set
  (so long names shrink instead of overflowing).
- Leave breathing room: keep at least ~40px between text baselines; do not place elements within 60px of the canvas edge
  unless drawing a border.
- Borders are rect elements with outline only. Decorative rules are line elements.
- If the user asks for verification/QR, add a qr element with data "{VERIFY_URL}".
- Colors are RGB arrays. Match the mood the user asks for (formal = muted golds/grays, playful = brighter accents).

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
