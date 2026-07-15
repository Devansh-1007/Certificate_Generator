"""
Batch job orchestration for the bulk pipeline.

A job moves through:  PENDING_REVIEW -> RENDERING -> DONE (or FAILED).

Upload creates a PENDING_REVIEW job holding the parsed rows + anomaly report.
After the human approves (maker-checker), `start_render` spawns a daemon thread
that renders each row through the template engine, records each certificate in
CERTIFICATE_DETAILS, zips the outputs, and advances the job to DONE.

DB helpers here are request-free (no Flask `request`) so the worker thread is
safe. Storage/DB stay optional-friendly: a missing bucket degrades to local
files exactly as the single-certificate path already does.
"""

import os
import json
import zipfile
import logging
import threading

from config import allCertImgPath, allCertPdfPath
from dataHandling import configureMySQL
from certificates import render_certificate

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Where per-job zip bundles are written.
BATCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "All_Batches")


def _sanitize(name):
    """Make a roster value safe to use as a filename / certificate name."""
    cleaned = "".join(c for c in (name or "") if c.isalnum() or c in " -_").strip()
    return cleaned or "certificate"


# --------------------------------------------------------------------------- #
# Request-free DB access
# --------------------------------------------------------------------------- #

def create_job(client_id, template_name, name_field, rows, report):
    db = configureMySQL()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO BATCH_JOBS "
        "(`CLIENT_ID`,`TEMPLATE_NAME`,`NAME_FIELD`,`STATUS`,`TOTAL`,`ROWS_JSON`,`ANOMALIES_JSON`) "
        "VALUES (%s,%s,%s,'PENDING_REVIEW',%s,%s,%s)",
        (client_id, template_name, name_field, len(rows),
         json.dumps(rows), json.dumps(report)),
    )
    db.commit()
    return cur.lastrowid


def get_job(client_id, job_id):
    db = configureMySQL()
    cur = db.cursor(dictionary=True)
    cur.execute(
        "SELECT * FROM BATCH_JOBS WHERE JOB_ID=%s AND CLIENT_ID=%s",
        (job_id, client_id),
    )
    row = cur.fetchone()
    if not row:
        return None
    for col in ("ROWS_JSON", "ANOMALIES_JSON", "ERRORS_JSON"):
        if row.get(col):
            try:
                row[col] = json.loads(row[col])
            except (TypeError, ValueError):
                pass
    return row


def list_jobs(client_id):
    db = configureMySQL()
    cur = db.cursor(dictionary=True)
    cur.execute(
        "SELECT JOB_ID, TEMPLATE_NAME, STATUS, TOTAL, PROCESSED, SUCCEEDED, FAILED, "
        "CREATED_ON, UPDATED_ON FROM BATCH_JOBS WHERE CLIENT_ID=%s ORDER BY JOB_ID DESC",
        (client_id,),
    )
    return cur.fetchall()


def _update(job_id, **fields):
    if not fields:
        return
    cols = ", ".join("`{}`=%s".format(k) for k in fields)
    db = configureMySQL()
    cur = db.cursor()
    cur.execute(
        "UPDATE BATCH_JOBS SET " + cols + ", `UPDATED_ON`=NOW() WHERE JOB_ID=%s",
        (*fields.values(), job_id),
    )
    db.commit()


def _insert_certificate_row(client_id, cert_name, img_path, pdf_path, b64):
    """Request-free equivalent of dataHandling.insertCertificate."""
    db = configureMySQL()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO CERTIFICATE_DETAILS "
        "(`CERTIFICATE_NAME`,`CERTIFICATE_IMG_PATH`,`CREATED_BY`,`UPDATED_BY`,"
        "`CERTIFICATE_PDF_PATH`,`UPDATED_ON`,`CLIENT_ID`,`BASE64`) "
        "VALUES (%s,%s,%s,%s,%s,NOW(),%s,%s)",
        (cert_name, img_path, client_id, client_id, pdf_path, client_id, b64),
    )
    db.commit()


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

def start_render(client_id, job_id, rows, template, name_field):
    """Kick off background rendering; returns immediately."""
    _update(job_id, STATUS="RENDERING", TOTAL=len(rows),
            PROCESSED=0, SUCCEEDED=0, FAILED=0, ERRORS_JSON=json.dumps([]))
    worker = threading.Thread(
        target=_render_job,
        args=(client_id, job_id, rows, template, name_field),
        daemon=True,
    )
    worker.start()


def _render_job(client_id, job_id, rows, template, name_field):
    processed = succeeded = failed = 0
    errors = []
    outputs = []  # (arcname, filepath) pairs for the zip

    for i, row in enumerate(rows):
        cert_name = _sanitize(row.get(name_field, ""))
        try:
            result = render_certificate(cert_name, client_id, template=template, overrides=row)
            det = result["CERTIFICATE_DETAILS"]
            try:
                _insert_certificate_row(
                    client_id, cert_name, det.get("IMAGE_URL"), det.get("PDF_URL"), det["BASE64"]
                )
            except Exception as db_err:  # noqa: BLE001
                # A duplicate name (or absent DB) shouldn't lose the rendered file.
                logging.warning("Row %s: DB record skipped (%s)", i + 1, db_err)
            if det.get("IMG_PATH"):
                outputs.append((cert_name + ".png", det["IMG_PATH"]))
            if det.get("PDF_PATH"):
                outputs.append((cert_name + ".pdf", det["PDF_PATH"]))
            succeeded += 1
        except Exception as e:  # noqa: BLE001
            failed += 1
            errors.append({"row": i + 1, "name": cert_name, "error": str(e)})
            logging.error("Row %s (%s) failed: %s", i + 1, cert_name, e)

        processed += 1
        _update(job_id, PROCESSED=processed, SUCCEEDED=succeeded, FAILED=failed)

    zip_path = None
    if outputs:
        try:
            zip_path = _bundle(client_id, job_id, outputs)
        except Exception as e:  # noqa: BLE001
            logging.error("Zip bundling failed for job %s: %s", job_id, e)

    _update(
        job_id,
        STATUS="DONE",
        PROCESSED=processed,
        SUCCEEDED=succeeded,
        FAILED=failed,
        ZIP_PATH=zip_path,
        ERRORS_JSON=json.dumps(errors),
    )
    logging.info("Batch job %s done: %s ok, %s failed", job_id, succeeded, failed)


def _bundle(client_id, job_id, outputs):
    job_dir = os.path.join(BATCH_DIR, client_id)
    os.makedirs(job_dir, exist_ok=True)
    zip_path = os.path.join(job_dir, "batch_{}.zip".format(job_id))
    seen = {}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, filepath in outputs:
            if not os.path.exists(filepath):
                continue
            # de-collide identical certificate names within the bundle
            final = arcname
            n = seen.get(arcname, 0)
            if n:
                stem, ext = os.path.splitext(arcname)
                final = "{}_{}{}".format(stem, n + 1, ext)
            seen[arcname] = n + 1
            zf.write(filepath, final)
    return zip_path
