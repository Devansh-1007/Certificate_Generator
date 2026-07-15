"""
Account / dashboard support endpoints (client-protected).

GET    /stats                -> per-client counts for the dashboard
DELETE /templates/<name>     -> delete a saved template
"""

import logging

from flask import Blueprint, jsonify, g

from middleware import require_client
from dataHandling import configureMySQL

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

account_bp = Blueprint("account", __name__)


def _count(cur, table, client_id):
    try:
        cur.execute("SELECT COUNT(*) FROM {} WHERE CLIENT_ID=%s".format(table), (client_id,))
        return cur.fetchone()[0]
    except Exception:  # noqa: BLE001 - table may not exist yet
        return 0


@account_bp.route("/stats", methods=["GET"])
@require_client
def stats():
    try:
        db = configureMySQL()
        cur = db.cursor()
        data = {
            "certificates": _count(cur, "CERTIFICATE_DETAILS", g.client_id),
            "ids": _count(cur, "ID_DETAILS", g.client_id),
            "templates": _count(cur, "TEMPLATE_DETAILS", g.client_id),
            "batches": _count(cur, "BATCH_JOBS", g.client_id),
            "verifiable": _count(cur, "CERTIFICATE_VERIFY", g.client_id),
        }
        return jsonify({"status": "Success", "STATS": data})
    except Exception as e:  # noqa: BLE001
        logging.error("stats failed: %s", e)
        return jsonify({"status": "Success", "STATS": {
            "certificates": 0, "ids": 0, "templates": 0, "batches": 0, "verifiable": 0,
        }})


@account_bp.route("/templates/<name>", methods=["DELETE"])
@require_client
def delete_template(name):
    try:
        db = configureMySQL()
        cur = db.cursor()
        cur.execute(
            "DELETE FROM TEMPLATE_DETAILS WHERE CLIENT_ID=%s AND TEMPLATE_NAME=%s",
            (g.client_id, name),
        )
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"description": "Template not found"}), 404
        return jsonify({"status": "Success", "TEMPLATE_NAME": name})
    except Exception as e:  # noqa: BLE001
        logging.error("delete_template failed: %s", e)
        return jsonify({"description": "Delete failed", "error": str(e)}), 500
