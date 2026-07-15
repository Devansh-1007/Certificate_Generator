"""
Certificate verification.

Public (no auth):
    GET  /verify/<uid>            -> JSON verification result (genuine/tampered/revoked)

Client-protected:
    GET  /myCertificates          -> this client's issued certificates (uid + status)
    POST /revokeCertificate/<uid> -> mark a certificate revoked
    POST /reinstateCertificate/<uid> -> undo a revocation
"""

import logging

from flask import Blueprint, jsonify, g

from middleware import require_client
import verification

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

verify_bp = Blueprint("verify", __name__)


@verify_bp.route("/verify/<uid>", methods=["GET"])
def verify(uid):
    result = verification.public_result(uid)
    status = 200 if result.get("valid") else 404 if result.get("reason") == "not_found" else 200
    return jsonify(result), status


@verify_bp.route("/myCertificates", methods=["GET"])
@require_client
def my_certificates():
    try:
        records = verification.list_records(g.client_id)
        for r in records:
            if r.get("CREATED_ON") is not None:
                r["CREATED_ON"] = str(r["CREATED_ON"])
        return jsonify({"status": "Success", "CERTIFICATES": records})
    except Exception as e:  # noqa: BLE001
        logging.error("myCertificates failed: %s", e)
        return jsonify({"description": "Failed to list certificates", "error": str(e)}), 500


@verify_bp.route("/revokeCertificate/<uid>", methods=["POST"])
@require_client
def revoke(uid):
    ok = verification.set_status(g.client_id, uid, "REVOKED")
    if not ok:
        return jsonify({"description": "Certificate not found for this client"}), 404
    return jsonify({"status": "Success", "CERT_UID": uid, "STATUS": "REVOKED"})


@verify_bp.route("/reinstateCertificate/<uid>", methods=["POST"])
@require_client
def reinstate(uid):
    ok = verification.set_status(g.client_id, uid, "VALID")
    if not ok:
        return jsonify({"description": "Certificate not found for this client"}), 404
    return jsonify({"status": "Success", "CERT_UID": uid, "STATUS": "VALID"})
