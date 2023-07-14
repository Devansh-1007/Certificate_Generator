import logging
from flask import jsonify
from authentication import *
from aes_token import *


def loginClient(CLIENT_ID, CLIENT_NAME, PASSWORD):
    try:
        if verify_Client(CLIENT_ID, CLIENT_NAME, PASSWORD, 'CLIENT_DETAILS'):
            logging.info("Client logged in successfully")
            SECRET_KEY = getClientInfo('CLIENT_SECRET_KEY',
                                       CLIENT_ID, 'CLIENT_DETAILS')
            if SECRET_KEY is None:
                return jsonify({'error': 'Login failed'}), 500
            IV = getClientInfo('CLIENT_IV',
                               CLIENT_ID, 'CLIENT_DETAILS')
            if IV is None:
                return jsonify({'error': 'Login failed'}), 500
            access_token = encrypt(SECRET_KEY, IV, CLIENT_ID)
            logging.info("Access token created successfully")
            return jsonify({'access_token': access_token}), 200
        else:
            logging.error("Invalid login credentials")
            return jsonify({'error': 'Invalid login credentials'}), 401
    except Exception as error:
        logging.error("An error occurred during login: %s", str(error))
        return jsonify({'error': 'Login failed'}), 500
