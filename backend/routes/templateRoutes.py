"""
Template + AI designer endpoints — all protected by require_client.

POST /designTemplate   {"PROMPT": "..."}                      -> AI-designed template JSON
POST /renderPreview    {"TEMPLATE": {...}, "DATA": {...}}     -> PNG preview (base64)
POST /saveTemplate     {"TEMPLATE": {...}}                    -> persist template for client
GET  /templates                                               -> list this client's templates
"""

import io
import json
import base64
import logging

from flask import Blueprint, request, jsonify, g

from middleware import require_client
from dataHandling import configureMySQL
from templateEngine import validate_template, render_template, extract_placeholders
from aiDesigner import design_template

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

templates_bp = Blueprint("templates", __name__)


@templates_bp.route("/designTemplate", methods=["POST"])
@require_client
def design():
    data = request.get_json() or {}
    prompt = data.get("PROMPT", "").strip()
    if not prompt:
        return jsonify({"description": "PROMPT is required"}), 400

    result = design_template(prompt)
    if not result["ok"]:
        return jsonify({
            "status": "Error",
            "description": "Agent could not produce a valid template",
            "TRACE": result["trace"],
        }), 422

    template = result["template"]
    return jsonify({
        "status": "Success",
        "TEMPLATE": template,
        "PLACEHOLDERS": extract_placeholders(template),
        "ATTEMPTS": result["attempts"],
        "TRACE": result["trace"],
    })


@templates_bp.route("/renderPreview", methods=["POST"])
@require_client
def preview():
    data = request.get_json() or {}
    template = data.get("TEMPLATE")
    if not template:
        return jsonify({"description": "TEMPLATE is required"}), 400

    ok, errors = validate_template(template)
    if not ok:
        return jsonify({"status": "Error", "ERRORS": errors}), 400

    values = data.get("DATA") or {}
    for name in extract_placeholders(template):
        values.setdefault(name, "[" + name + "]")

    image = render_template(template, values)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return jsonify({
        "status": "Success",
        "BASE64": base64.b64encode(buf.getvalue()).decode("utf-8"),
    })


@templates_bp.route("/saveTemplate", methods=["POST"])
@require_client
def save():
    data = request.get_json() or {}
    template = data.get("TEMPLATE")
    if not template:
        return jsonify({"description": "TEMPLATE is required"}), 400

    ok, errors = validate_template(template)
    if not ok:
        return jsonify({"status": "Error", "ERRORS": errors}), 400

    client = g.client_id
    mydb = configureMySQL()
    cursor = mydb.cursor()
    sql = (
        "INSERT INTO TEMPLATE_DETAILS (`CLIENT_ID`,`TEMPLATE_NAME`,`TEMPLATE_JSON`,`CREATED_BY`,`UPDATED_BY`,`UPDATED_ON`) "
        "VALUES (%s,%s,%s,%s,%s,NOW()) "
        "ON DUPLICATE KEY UPDATE TEMPLATE_JSON=VALUES(TEMPLATE_JSON), UPDATED_BY=VALUES(UPDATED_BY), UPDATED_ON=NOW()"
    )
    try:
        cursor.execute(sql, (client, template["name"], json.dumps(template), client, client))
        mydb.commit()
        logging.info("Template '%s' saved for client '%s'", template["name"], client)
        return jsonify({"status": "Success", "TEMPLATE_NAME": template["name"]})
    except Exception as e:
        logging.error("Failed to save template for client '%s': %s", client, str(e))
        return jsonify({"status": "Error", "description": "Database insert failed"}), 500


@templates_bp.route("/templates", methods=["GET"])
@require_client
def list_templates():
    mydb = configureMySQL()
    cursor = mydb.cursor()
    cursor.execute(
        "SELECT TEMPLATE_NAME, TEMPLATE_JSON, UPDATED_ON FROM TEMPLATE_DETAILS WHERE CLIENT_ID = %s",
        (g.client_id,),
    )
    rows = cursor.fetchall()
    return jsonify({
        "status": "Success",
        "TEMPLATES": [
            {"TEMPLATE_NAME": r[0], "TEMPLATE": json.loads(r[1]), "UPDATED_ON": str(r[2])}
            for r in rows
        ],
    })
