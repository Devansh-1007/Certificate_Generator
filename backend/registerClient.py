import jwt
from authentication import *
from dataHandling import *
from flask import jsonify
from config import *


def registerClient(Client):
    checkId = verify_ClientID(Client.CLIENT_ID, "CLIENT_DETAILS")
    if checkId:
        details = {
            "status": "Success",
            "description": "Client already exists",
        }
        logging.info("Client already exists for CLIENT_ID: %s", Client.CLIENT_ID)
        return jsonify(details)
    else:
        try:
            if insertClient(Client, "CLIENT_DETAILS"):
                logging.info("Client created for CLIENT_ID: %s", Client.CLIENT_ID)
                return jsonify(description="Client Registration Successful")
            else:
                return jsonify(description="Client Registration Failed")
        except Exception as error:
            return str(error), 500
