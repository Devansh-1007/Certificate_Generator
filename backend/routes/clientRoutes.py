"""Client account routes. /loginClient is unprotected; /registerClient is admin-only."""

import logging

from flask import Blueprint, request, jsonify
from flasgger import swag_from
from werkzeug.security import generate_password_hash

from middleware import require_admin
from models import Client
from registerClient import registerClient
from loginClient import loginClient
from routes import swagger_doc

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

client_bp = Blueprint("clients", __name__)


@client_bp.route("/registerClient", methods=["POST"])
@swag_from(swagger_doc("register_client.yaml"))
@require_admin
def register():
    data = request.get_json()
    hash_password = generate_password_hash(data["PASSWORD"])
    client = Client(data["CLIENT_ID"], data["CLIENT_NAME"], hash_password, "NULL", "NULL")
    try:
        return registerClient(client)
    except Exception as error:
        return str(error), 500


@client_bp.route("/loginClient", methods=["POST"])
@swag_from(swagger_doc("login_client.yaml"))
def login():
    data = request.get_json()
    try:
        return loginClient(data["CLIENT_ID"], data["CLIENT_NAME"], data["PASSWORD"])
    except Exception as error:
        return str(error), 500
