from config import *
import MySQLdb
import logging
from dataHandling import *
from werkzeug.security import check_password_hash
from flask import jsonify
from aes_token import *


# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def configureMySQL():
    return MySQLdb.connect(mysql_host, mysql_user,
                           mysql_pass, mysql_db, mysql_port)


def verify_Client(CLIENT_ID, CLIENT_NAME, PASSWORD, TABLE):
    mydb = configureMySQL()
    cursor = mydb.cursor()
    sql = "SELECT * FROM " + TABLE + \
        " WHERE CLIENT_ID = %s  AND CLIENT_NAME =%s "
    cursor.execute(sql, (CLIENT_ID, CLIENT_NAME))
    result = cursor.fetchone()
    stored_password = getClientInfo('PASSWORD', CLIENT_ID, 'CLIENT_DETAILS')
    password_result = check_password_hash(stored_password, PASSWORD)
    if result is not None and password_result:
        logging.info("Client ID '%s' authenticated in table '%s'",
                     CLIENT_ID, TABLE)
        return True
    else:
        logging.info("Client ID '%s' is not authenticated in table '%s'",
                     CLIENT_ID, TABLE)
        return False


def verify_ClientID(CLIENT_ID, TABLE):
    mydb = configureMySQL()
    cursor = mydb.cursor()
    sql = "SELECT CLIENT_ID FROM " + TABLE + \
        " WHERE CLIENT_ID = %s "
    cursor.execute(sql, (CLIENT_ID,))
    result = cursor.fetchone()
    if result is not None:
        logging.info("Client ID '%s' exist in table '%s'",
                     CLIENT_ID, TABLE)
        return True
    else:
        logging.info("Client ID '%s' does not exist in table '%s'",
                     CLIENT_ID, TABLE)
        return False


def verifyToken(CURRENT_CLIENT, TOKEN):
    CURRENT_KEY = getClientInfo('CLIENT_SECRET_KEY',
                                CURRENT_CLIENT, 'CLIENT_DETAILS')
    if CURRENT_KEY is None:
        return jsonify({'error': 'Enter Valid Client Id'}), 500

    CURRENT_IV = getClientInfo(
        'CLIENT_IV', CURRENT_CLIENT, 'CLIENT_DETAILS')
    if CURRENT_IV is None:
        return jsonify({'error': 'Enter Valid Client Id'}), 500

    try:
        return decrypt(CURRENT_KEY, CURRENT_IV, TOKEN)
    except Exception as e:
        return jsonify({"description": "Invalid token"}), 401


def verify_Certificate(CERTIFICATE_NAME, CLIENT_ID, TABLE):
    mydb = configureMySQL()
    cursor = mydb.cursor()
    sql = "SELECT CERTIFICATE_NAME FROM " + TABLE + \
        " WHERE CLIENT_ID = %s AND CERTIFICATE_NAME =%s"
    cursor.execute(sql, (CLIENT_ID, CERTIFICATE_NAME))
    result = cursor.fetchone()
    if result is not None:
        logging.info("Certificate '%s'exist in table '%s'",
                     CERTIFICATE_NAME, TABLE)
        return True
    else:
        logging.info("Certificate %s do not exist in table '%s'",
                     CERTIFICATE_NAME, TABLE)
        return False


def verify_ID(ID_NAME, CLIENT_ID, TABLE):
    mydb = configureMySQL()
    cursor = mydb.cursor()
    sql = "SELECT ID_NAME FROM " + TABLE + \
        " WHERE CLIENT_ID = %s AND ID_NAME =%s"
    cursor.execute(sql, (CLIENT_ID, ID_NAME))
    result = cursor.fetchone()
    if result is not None:
        logging.info("Id '%s'exist in table '%s'",
                     ID_NAME, TABLE)
        return True
    else:
        logging.info("Id %s do not exist in table '%s'",
                     ID_NAME, TABLE)
        return False


def verifyAdmin(TOKEN):
    if TOKEN == admin_token:
        logging.info("Admin access verified")
        return True, 200
    else:
        logging.info("Admin access not verified")
        return False, 401
