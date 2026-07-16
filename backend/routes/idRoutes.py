"""ID-card routes — all protected by require_client."""

import logging

from flask import Blueprint, request, jsonify, send_file, g
from flasgger import swag_from

from config import bucket, allIdImgPath, allIdPdfPath
from middleware import require_client
from models import Client, IdCard
from idCard import generateID
from awsS3 import downloadFile
from authentication import verify_ID
from dataHandling import getIDInfo, insertId, getAllFile
from routes import swagger_doc

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

id_bp = Blueprint("ids", __name__)


@id_bp.route("/generateId", methods=["POST"])
@swag_from(swagger_doc("generate_id.yaml"))
@require_client
def generateId():
    try:
        data = request.get_json()
        ID_NAME = data["ID_NAME"]
        CURRENT_CLIENT = g.client_id

        if verify_ID(ID_NAME, CURRENT_CLIENT, "ID_DETAILS"):
            details = {
                "status": "Success",
                "description": "Id already exists",
                "ID_DETAILS": {
                    "ID_NAME": ID_NAME,
                    "CREATED_BY": CURRENT_CLIENT,
                    "IMAGE_URL": getIDInfo("ID_IMG_PATH", ID_NAME, "ID_DETAILS"),
                    "PDF_URL": getIDInfo("ID_PDF_PATH", ID_NAME, "ID_DETAILS"),
                },
            }
            logging.info("Id already exists for CLIENT_ID: %s", CURRENT_CLIENT)
            return jsonify(details)

        client = Client(CURRENT_CLIENT, "NULL", "NULL", "NULL", "NULL")
        result = generateID(ID_NAME, client.CLIENT_ID, ORG_NAME=data.get("ORG_NAME")).json
        client.ID = IdCard(ID_NAME, "NULL", "NULL")
        client.ID.ID_IMG_PATH = result["ID_DETAILS"]["IMAGE_URL"]
        client.ID.ID_PDF_PATH = result["ID_DETAILS"]["PDF_URL"]

        if insertId(client.ID, client, "ID_DETAILS"):
            return jsonify(result)
        return jsonify({"description": "Data cannot be inserted into the database"}), 401
    except Exception as error:
        logging.error("An error occurred. Id cannot be generated: %s", str(error))
        return str(error), 500


@id_bp.route("/getId", methods=["GET"])
@swag_from(swagger_doc("get_id.yaml"))
@require_client
def getId():
    ID_NAME = request.args.get("ID_NAME")
    EXTENSION = request.args.get("EXTENSION")
    CURRENT_CLIENT = g.client_id
    try:
        if EXTENSION == "pdf":
            downloadFile(bucket, allIdPdfPath + "/" + CURRENT_CLIENT, str(ID_NAME) + ".pdf")
            file = allIdPdfPath + "/" + CURRENT_CLIENT + "/" + ID_NAME + ".pdf"
            logging.info("File retrieved: %s", file)
            return send_file(file, mimetype="application/pdf")
        elif EXTENSION == "img":
            downloadFile(bucket, allIdImgPath + "/" + CURRENT_CLIENT, str(ID_NAME) + ".png")
            file = allIdImgPath + "/" + CURRENT_CLIENT + "/" + ID_NAME + ".png"
            logging.info("File retrieved: %s", file)
            return send_file(file, mimetype="image/png")
        logging.warning("Invalid extension or filename: %s, %s", EXTENSION, ID_NAME)
        return "Invalid extension or filename"
    except Exception as e:
        logging.error("An error occurred while retrieving file: %s", str(e))
        return "File Not Found"


@id_bp.route("/idCards", methods=["GET"])
@require_client
def list_id_cards():
    """List this client's ID cards (name + created date) for the ID cards page."""
    from dataHandling import configureMySQL
    try:
        db = configureMySQL()
        cur = db.cursor()
        cur.execute(
            "SELECT ID_NAME, CREATED_ON FROM ID_DETAILS WHERE CLIENT_ID=%s ORDER BY CREATED_ON DESC",
            (g.client_id,),
        )
        rows = cur.fetchall()
        return jsonify({
            "status": "Success",
            "ID_CARDS": [{"ID_NAME": r[0], "CREATED_ON": str(r[1])} for r in rows],
        })
    except Exception as error:
        return jsonify({"description": "Failed to list ID cards", "error": str(error)}), 500


@id_bp.route("/getAllId", methods=["GET"])
@swag_from(swagger_doc("get_AllId.yaml"))
@require_client
def getAllId():
    try:
        return jsonify({"base64_data_list": getAllFile("ID_DETAILS")})
    except Exception as error:
        return jsonify({"description": "Failed to retrieve files", "error": str(error)}), 500
