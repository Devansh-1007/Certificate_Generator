"""
Run the AI-designer eval set and report quality metrics.

For each design prompt we ask the agent for a template, then score it on four
independent axes:

    agent_ok     — the agent returned a template within MAX_ATTEMPTS
    schema_valid — the template passes the JSON-schema + semantic validation
    render_ok    — it actually renders to an image with sample data
    layout_ok    — no heuristic layout warnings (overlaps / overflow)

Usage:
    python -m evals.run_evals                # uses the configured LLM_PROVIDER
    python -m evals.run_evals --limit 5      # first 5 prompts only
    python -m evals.run_evals --fake         # offline smoke (no API key/network)

Writes evals/results/latest.json and evals/results/latest.md.
Exit code is non-zero if any axis falls below --min-pass (default 0.9), so this
can gate CI.
"""

import os
import sys
import json
import argparse

from templateEngine.schema import validate_template
from templateEngine.renderer import render_template, layout_report, extract_placeholders
from aiDesigner.agent import design_template

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


class _FakeLLM:
    """Offline stand-in: always emits the bundled default template."""

    def __init__(self):
        preset = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "templateEngine", "presets", "default_certificate.json")
        with open(preset) as f:
            self._template = json.load(f)

    def chat(self, messages, tool):
        return {"tool_input": self._template, "text": ""}


def _sample_values(template):
    return {name: "[" + name + "]" for name in extract_placeholders(template)}


def score_one(prompt, llm=None):
    row = {"prompt": prompt, "agent_ok": False, "schema_valid": False,
           "render_ok": False, "layout_ok": False, "attempts": None, "error": None}
    try:
        result = design_template(prompt, llm=llm)
    except Exception as e:  # noqa: BLE001
        row["error"] = "agent: " + str(e)
        return row

    row["attempts"] = result.get("attempts")
    template = result.get("template")
    row["agent_ok"] = bool(result.get("ok") and template)
    if not template:
        return row

    row["schema_valid"] = validate_template(template)[0]
    try:
        render_template(template, _sample_values(template))
        row["render_ok"] = True
    except Exception as e:  # noqa: BLE001
        row["error"] = "render: " + str(e)
    row["layout_ok"] = len(layout_report(template)) == 0
    return row


AXES = ["agent_ok", "schema_valid", "render_ok", "layout_ok"]


def summarize(rows):
    n = len(rows) or 1
    rates = {axis: sum(1 for r in rows if r[axis]) / n for axis in AXES}
    attempts = [r["attempts"] for r in rows if r["attempts"]]
    return {
        "total": len(rows),
        "pass_rates": rates,
        "avg_attempts": round(sum(attempts) / len(attempts), 2) if attempts else None,
    }


def to_markdown(summary, rows, provider):
    lines = [
        "# AI Designer eval results",
        "",
        "Provider: `{}`  ·  Prompts: {}  ·  Avg attempts: {}".format(
            provider, summary["total"], summary["avg_attempts"]),
        "",
        "| Axis | Pass rate |",
        "| --- | --- |",
    ]
    for axis in AXES:
        lines.append("| {} | {:.0%} |".format(axis, summary["pass_rates"][axis]))
    lines += ["", "## Per-prompt", "", "| # | agent | schema | render | layout | attempts | prompt |",
              "| - | - | - | - | - | - | - |"]
    tick = lambda b: "✅" if b else "❌"  # noqa: E731
    for i, r in enumerate(rows, 1):
        lines.append("| {} | {} | {} | {} | {} | {} | {} |".format(
            i, tick(r["agent_ok"]), tick(r["schema_valid"]), tick(r["render_ok"]),
            tick(r["layout_ok"]), r["attempts"] if r["attempts"] is not None else "-",
            r["prompt"][:60]))
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run AI-designer evals")
    parser.add_argument("--limit", type=int, default=None, help="only the first N prompts")
    parser.add_argument("--fake", action="store_true", help="offline fake LLM (no network)")
    parser.add_argument("--min-pass", type=float, default=0.9, help="fail if any axis below this")
    args = parser.parse_args(argv)

    from evals.prompts import PROMPTS
    prompts = PROMPTS[: args.limit] if args.limit else PROMPTS
    provider = "fake" if args.fake else os.getenv("LLM_PROVIDER", "openai")

    rows = []
    for i, prompt in enumerate(prompts, 1):
        llm = _FakeLLM() if args.fake else None
        row = score_one(prompt, llm=llm)
        rows.append(row)
        flags = "".join("1" if row[a] else "0" for a in AXES)
        print("[{}/{}] {} {}".format(i, len(prompts), flags, prompt[:55]))

    summary = summarize(rows)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "latest.json"), "w") as f:
        json.dump({"provider": provider, "summary": summary, "rows": rows}, f, indent=2)
    with open(os.path.join(RESULTS_DIR, "latest.md"), "w", encoding="utf-8") as f:
        f.write(to_markdown(summary, rows, provider))

    print("\n== Summary ({}) ==".format(provider))
    for axis in AXES:
        print("  {:<13} {:.0%}".format(axis, summary["pass_rates"][axis]))
    print("  avg attempts  {}".format(summary["avg_attempts"]))
    print("  results -> evals/results/latest.md")

    worst = min(summary["pass_rates"].values())
    return 0 if worst >= args.min_pass else 1


if __name__ == "__main__":
    sys.exit(main())
