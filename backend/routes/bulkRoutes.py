"""
Bulk pipeline routes — all protected by require_client (maker-checker flow).

POST /bulk/upload            (multipart) file=<csv/xlsx> TEMPLATE_NAME MAPPING?
                             -> parse + anomaly review; creates a PENDING_REVIEW job
GET  /bulk/jobs              -> this client's batch jobs
GET  /bulk/jobs/<id>         -> one job (rows, anomalies, progress, errors)
POST /bulk/jobs/<id>/approve {"ROWS": [...]} -> start background render (maker-checker)
GET  /bulk/jobs/<id>/download -> the rendered certificates as a zip
"""

import re
import json
import logging

from flask import Blueprint, request, jsonify, g, send_file, Response

from middleware import require_client
from dataHandling import configureMySQL
from certificates import default_template
from templateEngine import extract_placeholders
from bulk import parse_table, map_rows, detect_anomalies, suggest_rows, ParseError
from bulk.parser import MAX_ROWS
from bulk.jobs import create_job, get_job, list_jobs, start_render

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

bulk_bp = Blueprint("bulk", __name__)

DEFAULT_TEMPLATE_NAME = "Classic Achievement"


def _resolve_template(client_id, template_name):
    """Return the template JSON for this client, or the built-in default."""
    if not template_name or template_name == DEFAULT_TEMPLATE_NAME:
        return default_template()
    db = configureMySQL()  # keep connection referenced (error 2055 otherwise)
    cur = db.cursor()
    cur.execute(
        "SELECT TEMPLATE_JSON FROM TEMPLATE_DETAILS WHERE CLIENT_ID=%s AND TEMPLATE_NAME=%s",
        (client_id, template_name),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return json.loads(row[0])


def _name_field(placeholders):
    return "RECIPIENT_NAME" if "RECIPIENT_NAME" in placeholders else (
        placeholders[0] if placeholders else "RECIPIENT_NAME"
    )


@bulk_bp.route("/bulk/upload", methods=["POST"])
@require_client
def upload():
    if "file" not in request.files:
        return jsonify({"description": "Upload a file under form field 'file'."}), 400
    upload_file = request.files["file"]
    file_bytes = upload_file.read()
    if not file_bytes:
        return jsonify({"description": "The uploaded file is empty."}), 400

    template_name = request.form.get("TEMPLATE_NAME", DEFAULT_TEMPLATE_NAME)
    template = _resolve_template(g.client_id, template_name)
    if template is None:
        return jsonify({"description": "Template '{}' not found".format(template_name)}), 404

    mapping = {}
    if request.form.get("MAPPING"):
        try:
            mapping = json.loads(request.form["MAPPING"])
        except ValueError:
            return jsonify({"description": "MAPPING must be valid JSON."}), 400

    try:
        rows = parse_table(upload_file.filename, file_bytes)
    except ParseError as e:
        return jsonify({"status": "Error", "description": str(e)}), 400

    if not rows:
        return jsonify({"status": "Error", "description": "No data rows found in the file."}), 400

    placeholders = extract_placeholders(template)
    if len(rows) > MAX_ROWS:
        return jsonify({
            "status": "Error",
            "description": "Roster has {} rows; the limit is {} per job. Split the file.".format(
                len(rows), MAX_ROWS
            ),
        }), 413

    mapped, unmapped, mapping_report = map_rows(rows, placeholders, mapping)
    name_field = _name_field(placeholders)
    report = detect_anomalies(mapped, name_field)
    suggested = suggest_rows(mapped, report)

    job_id = create_job(g.client_id, template_name, name_field, mapped, report)
    logging.info("Batch job %s created for client '%s' (%s rows)",
                 job_id, g.client_id, len(mapped))

    return jsonify({
        "status": "Success",
        "JOB_ID": job_id,
        "TEMPLATE_NAME": template_name,
        "NAME_FIELD": name_field,
        "COLUMNS": list(rows[0].keys()),
        "PLACEHOLDERS": placeholders,
        "MAPPING_REPORT": mapping_report,
        "UNMAPPED_PLACEHOLDERS": unmapped,
        "ROWS": mapped,
        "SUGGESTED_ROWS": suggested,
        "REPORT": report,
    })


@bulk_bp.route("/bulk/template", methods=["GET"])
@require_client
def roster_template():
    """
    Download a ready-to-fill CSV for the chosen template: one column per
    placeholder the design actually uses, plus two example rows. Removes the
    guesswork about which columns the importer expects.
    """
    import csv as _csv
    import io as _io

    template = _resolve_template(g.client_id, request.args.get("TEMPLATE_NAME"))
    if template is None:
        return jsonify({"description": "Template not found"}), 404

    placeholders = [p for p in extract_placeholders(template) if p != "VERIFY_URL"]
    if not placeholders:
        placeholders = ["RECIPIENT_NAME"]

    samples = {
        "RECIPIENT_NAME": ["Alice Sharma", "Rohan Mehta"],
        "EVENT_NAME": ["Annual Hackathon 2026", "Annual Hackathon 2026"],
        "ISSUE_DATE": ["15 July 2026", "15 July 2026"],
        "SIGNATORY_NAME": ["Dr. A. Sharma", "Dr. A. Sharma"],
        "SIGNATORY_TITLE": ["Director", "Director"],
        "ORG_NAME": ["CertifyAI", "CertifyAI"],
    }
    buf = _io.StringIO()
    writer = _csv.writer(buf)
    writer.writerow(placeholders)
    for i in range(2):
        writer.writerow([samples.get(p, ["Example " + p.title()] * 2)[i] for p in placeholders])

    filename = "roster-template-{}.csv".format(
        re.sub(r"[^A-Za-z0-9]+", "-", template.get("name", "certificate")).strip("-").lower()
    )
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=" + filename},
    )


@bulk_bp.route("/bulk/jobs", methods=["GET"])
@require_client
def jobs():
    rows = list_jobs(g.client_id)
    for r in rows:
        for col in ("CREATED_ON", "UPDATED_ON"):
            if r.get(col) is not None:
                r[col] = str(r[col])
    return jsonify({"status": "Success", "JOBS": rows})


@bulk_bp.route("/bulk/jobs/<int:job_id>", methods=["GET"])
@require_client
def job_detail(job_id):
    job = get_job(g.client_id, job_id)
    if not job:
        return jsonify({"description": "Job not found"}), 404
    for col in ("CREATED_ON", "UPDATED_ON"):
        if job.get(col) is not None:
            job[col] = str(job[col])
    return jsonify({"status": "Success", "JOB": job})


@bulk_bp.route("/bulk/jobs/<int:job_id>/approve", methods=["POST"])
@require_client
def approve(job_id):
    job = get_job(g.client_id, job_id)
    if not job:
        return jsonify({"description": "Job not found"}), 404
    if job["STATUS"] != "PENDING_REVIEW":
        return jsonify({"description": "Job already {}".format(job["STATUS"].lower())}), 409

    data = request.get_json(silent=True) or {}
    # Maker-checker: the approver sends back the final (possibly edited) rows.
    rows = data.get("ROWS") or job["ROWS_JSON"]
    if not rows:
        return jsonify({"description": "No rows to render."}), 400

    template = _resolve_template(g.client_id, job["TEMPLATE_NAME"])
    if template is None:
        return jsonify({"description": "Template no longer exists."}), 404

    start_render(g.client_id, job_id, rows, template, job["NAME_FIELD"])
    return jsonify({"status": "Success", "JOB_ID": job_id, "STATUS": "RENDERING", "TOTAL": len(rows)})


@bulk_bp.route("/bulk/jobs/<int:job_id>/download", methods=["GET"])
@require_client
def download(job_id):
    job = get_job(g.client_id, job_id)
    if not job:
        return jsonify({"description": "Job not found"}), 404
    zip_path = job.get("ZIP_PATH")
    if not zip_path:
        return jsonify({"description": "Nothing to download yet — job status is {}".format(
            job["STATUS"])}), 409
    try:
        return send_file(zip_path, mimetype="application/zip", as_attachment=True,
                         download_name="certificates_batch_{}.zip".format(job_id))
    except Exception as e:  # noqa: BLE001
        logging.error("Zip download failed for job %s: %s", job_id, e)
        return jsonify({"description": "Zip file missing on disk."}), 404
