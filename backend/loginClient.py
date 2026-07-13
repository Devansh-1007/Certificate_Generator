import logging

from flask import jsonify

from authentication import verify_Client
from auth_jwt import issue_token


def loginClient(CLIENT_ID, CLIENT_NAME, PASSWORD):
    try:
        if verify_Client(CLIENT_ID, CLIENT_NAME, PASSWORD, "CLIENT_DETAILS"):
            logging.info("Client logged in successfully")
            access_token = issue_token(CLIENT_ID, CLIENT_NAME, role="client")
            return jsonify({"access_token": access_token, "role": "client"}), 200
        logging.error("Invalid login credentials")
        return jsonify({"error": "Invalid login credentials"}), 401
    except Exception as error:
        logging.error("An error occurred during login: %s", str(error))
        return jsonify({"error": "Login failed"}), 500
