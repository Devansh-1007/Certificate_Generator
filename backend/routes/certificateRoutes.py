"""Certificate routes — all protected by require_client."""

import logging

from flask import Blueprint, request, jsonify, send_file, g
from flasgger import swag_from

from config import bucket, allCertImgPath, allCertPdfPath, base_url
from middleware import require_client
from models import Client, Certificate
from certificates import generateCert
from awsS3 import downloadFile
import verification
from dataHandling import (
    getCertificateInfo,
    insertCertificate,
    getAllFile,
    getCertificateDesigns,
)
from routes import swagger_doc

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

certificate_bp = Blueprint("certificates", __name__)


@certificate_bp.route("/generateCertificate", methods=["POST"])
@swag_from(swagger_doc("generate_certificate.yaml"))
@require_client
def generatecert():
    try:
        data = request.get_json()
        CERTIFICATE_NAME = data["CERTIFICATE_NAME"]
        CURRENT_CLIENT = g.client_id

        overrides = dict(data.get("DATA") or {})
        event = overrides.get("EVENT_NAME")
        issue_date = overrides.get("ISSUE_DATE")

        # A repeat is the same recipient AND event AND date — the same person may
        # hold many certificates. An exact repeat is treated as an accidental
        # double-submit and reported, unless the caller explicitly re-issues.
        if not data.get("REISSUE"):
            existing = verification.find_duplicate(CURRENT_CLIENT, CERTIFICATE_NAME, event, issue_date)
            if existing:
                return jsonify({
                    "status": "Duplicate",
                    "description": (
                        "'{}' already has a certificate for this event and date. "
                        "Change a detail, or re-issue to create another copy.".format(CERTIFICATE_NAME)
                    ),
                    "EXISTING_CERT_UID": existing,
                    "VERIFY_URL": "{}/verify/{}".format(
                        (base_url or "http://localhost:5000").rstrip("/"), existing
                    ),
                }), 409

        template = None
        template_name = data.get("TEMPLATE_NAME")
        if template_name and template_name != "Classic Achievement":
            import json as _json
            from dataHandling import configureMySQL
            db = configureMySQL()  # keep the connection referenced, or it is GC'd mid-query (error 2055)
            cur = db.cursor()
            cur.execute(
                "SELECT TEMPLATE_JSON FROM TEMPLATE_DETAILS WHERE CLIENT_ID=%s AND TEMPLATE_NAME=%s",
                (CURRENT_CLIENT, template_name),
            )
            row = cur.fetchone()
            if row is None:
                return jsonify({"description": "Template '" + template_name + "' not found"}), 404
            template = _json.loads(row[0])

        # Issue a verifiable, signed UID and point the QR at the public verify URL.
        cert_uid, _ = verification.create_record(CURRENT_CLIENT, CERTIFICATE_NAME, event, issue_date)
        overrides["VERIFY_URL"] = "{}/verify/{}".format(
            (base_url or "http://localhost:5000").rstrip("/"), cert_uid
        )

        client = Client(CURRENT_CLIENT, "NULL", "NULL", "NULL", "NULL")
        result = generateCert(
            CERTIFICATE_NAME, client.CLIENT_ID,
            template=template, overrides=overrides, file_key=cert_uid,
        ).json
        result["CERTIFICATE_DETAILS"]["CERT_UID"] = cert_uid
        result["CERTIFICATE_DETAILS"]["VERIFY_URL"] = overrides["VERIFY_URL"]
        client.CERTIFICATE = Certificate(CERTIFICATE_NAME, "NULL", "NULL", "NULL")
        client.CERTIFICATE.CERTIFICATE_IMG_PATH = result["CERTIFICATE_DETAILS"]["IMAGE_URL"]
        client.CERTIFICATE.CERTIFICATE_PDF_PATH = result["CERTIFICATE_DETAILS"]["PDF_URL"]
        client.CERTIFICATE.CERTIFICATE_BASE64 = result["CERTIFICATE_DETAILS"]["BASE64"]

        if insertCertificate(client.CERTIFICATE, client, "CERTIFICATE_DETAILS"):
            return jsonify(result)
        return jsonify({"description": "Data cannot be inserted into the database"}), 401
    except Exception as error:
        logging.error("An error occurred. Certificate cannot be generated: %s", str(error))
        return str(error), 500


@certificate_bp.route("/getCertificate", methods=["GET"])
@swag_from(swagger_doc("get_certificate.yaml"))
@require_client
def getCert():
    CERTIFICATE_NAME = request.args.get("CERT_UID") or request.args.get("CERTIFICATE_NAME")
    EXTENSION = request.args.get("EXTENSION")
    CURRENT_CLIENT = g.client_id
    try:
        if EXTENSION == "pdf":
            downloadFile(bucket, allCertPdfPath + "/" + CURRENT_CLIENT, str(CERTIFICATE_NAME) + ".pdf")
            file = allCertPdfPath + "/" + CURRENT_CLIENT + "/" + CERTIFICATE_NAME + ".pdf"
            logging.info("File retrieved: %s", file)
            return send_file(file, mimetype="application/pdf")
        elif EXTENSION == "img":
            downloadFile(bucket, allCertImgPath + "/" + CURRENT_CLIENT, str(CERTIFICATE_NAME) + ".png")
            file = allCertImgPath + "/" + CURRENT_CLIENT + "/" + CERTIFICATE_NAME + ".png"
            logging.info("File retrieved: %s", file)
            return send_file(file, mimetype="image/png")
        logging.warning("Invalid extension or filename: %s, %s", EXTENSION, CERTIFICATE_NAME)
        return "Invalid extension or filename"
    except Exception as e:
        logging.error("An error occurred while retrieving file: %s", str(e))
        return "File Not Found"


@certificate_bp.route("/getAllCertificate", methods=["GET"])
@swag_from(swagger_doc("get_AllCertificate.yaml"))
@require_client
def getAllCert():
    try:
        return jsonify({"base64_data_list": getAllFile("CERTIFICATE_DETAILS")})
    except Exception as error:
        return jsonify({"description": "Failed to retrieve files", "error": str(error)}), 500


@certificate_bp.route("/getCertificateDesigns", methods=["GET"])
@require_client
def getCertDesign():
    try:
        return jsonify({"base64_data_list": getCertificateDesigns("CERTIFICATE_DESIGNS")})
    except Exception as error:
        return jsonify({"description": "Failed to retrieve files", "error": str(error)}), 500
