from flask import request
from config import *
import MySQLdb
import logging
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes


# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def configureMySQL():
    return MySQLdb.connect(mysql_host, mysql_user,
                           mysql_pass, mysql_db, mysql_port)


def insertClient(Client, TABLE):
    if request.method == 'POST':
        mydb = configureMySQL()
        cursor = mydb.cursor()
        sql = "INSERT IGNORE INTO {0} (`CLIENT_ID`,`PASSWORD`, `CLIENT_NAME`, `CREATED_BY`,`CLIENT_SECRET_KEY`,`CLIENT_IV`) VALUES (%s, %s, %s, %s, %s, %s)".format(
            TABLE)
        KEY = get_random_bytes(32)
        IV = get_random_bytes(AES.block_size)
        values = (Client.CLIENT_ID, Client.PASSWORD, Client.CLIENT_NAME,
                  admin, KEY, IV)

        try:
            cursor.execute(sql, values)
            mydb.commit()
            logging.info(
                "Data inserted into table '%s' for Client with ID '%s'", TABLE, Client.CLIENT_ID)
            return True
        except Exception as e:
            logging.error("Failed to insert data into table '%s' for Client with ID '%s'. Error: %s",
                          TABLE, Client.CLIENT_ID, str(e))
            return False

# To change password or client id:


def updateClient(COLUMN, newValue, Client, TABLE):
    if request.method == 'POST':
        mydb = configureMySQL()
        cursor = mydb.cursor()
        sql = "UPDATE " + TABLE + \
            " SET "+COLUMN+" = %s , `UPDATED_ON` = NOW() WHERE `CLIENT_ID` = %s"
        try:
            cursor.execute(
                sql, (newValue, Client.CLIENT_ID))
            mydb.commit()
            logging.info(
                "Data updated in table '%s' for Client with ID '%s'", TABLE, Client.CLIENT_ID)
        except Exception as e:
            logging.error("Failed to update data in table '%s' for Client with ID '%s'. Error: %s",
                          TABLE, Client.CLIENT_ID, str(e))


def getClientInfo(COLUMN, CLIENT_ID, TABLE):
    mydb = configureMySQL()
    cursor = mydb.cursor()
    sql = "SELECT "+COLUMN + " FROM " + TABLE + " WHERE `CLIENT_ID` = %s"
    cursor.execute(sql, (CLIENT_ID,))
    result = cursor.fetchone()
    if result is not None:
        data = result[0]
        return data

    return None


def insertCertificate(CERTIFICATE, Client, TABLE):
    if request.method == 'POST':
        mydb = configureMySQL()
        cursor = mydb.cursor()
        sql = "INSERT INTO {0} (`CERTIFICATE_NAME`,`CERTIFICATE_IMG_PATH`,`CREATED_BY`,`UPDATED_BY`, `CERTIFICATE_PDF_PATH`, `UPDATED_ON`,`CLIENT_ID`,`BASE64`) VALUES (%s,%s,%s,%s,%s, NOW(),%s,%s)".format(
            TABLE)
        values = (CERTIFICATE.CERTIFICATE_NAME, CERTIFICATE.CERTIFICATE_IMG_PATH,
                  Client.CLIENT_ID, Client.CLIENT_ID, CERTIFICATE.CERTIFICATE_PDF_PATH, Client.CLIENT_ID, CERTIFICATE.CERTIFICATE_BASE64)

        try:
            cursor.execute(sql, values)
            mydb.commit()
            logging.info(
                "Data inserted in table '%s' for Client with ID '%s'", TABLE, Client.CLIENT_ID)
            return True
        except Exception as e:
            logging.error("Failed to update data in table '%s' for Client with ID '%s'. Error: %s",
                          TABLE, Client.CLIENT_ID, str(e))
            return False


def insertId(ID, Client, TABLE):
    if request.method == 'POST':
        mydb = configureMySQL()
        cursor = mydb.cursor()
        sql = "INSERT INTO {0} (`ID_NAME`,`ID_IMG_PATH`,`CREATED_BY`,`UPDATED_BY`, `ID_PDF_PATH`, `UPDATED_ON`,`CLIENT_ID`) VALUES (%s,%s,%s,%s,%s, NOW(),%s)".format(
            TABLE)
        values = (ID.ID_NAME, ID.ID_IMG_PATH,
                  Client.CLIENT_ID, Client.CLIENT_ID, ID.ID_PDF_PATH, Client.CLIENT_ID)

        try:
            cursor.execute(sql, values)
            mydb.commit()
            logging.info(
                "Data inserted in table '%s' for Client with ID '%s'", TABLE, Client.CLIENT_ID)
            return True
        except Exception as e:
            logging.error("Failed to update data in table '%s' for Client with ID '%s'. Error: %s",
                          TABLE, Client.CLIENT_ID, str(e))
            return False


def getCertificateInfo(COLUMN, CERTIFICATE_NAME, TABLE):
    mydb = configureMySQL()
    cursor = mydb.cursor()
    sql = "SELECT "+COLUMN + " FROM " + TABLE + " WHERE `CERTIFICATE_NAME` = %s"
    cursor.execute(sql, (CERTIFICATE_NAME,))
    result = cursor.fetchone()
    if result is not None:
        data = result[0]
        return data

    return None


def getIDInfo(COLUMN, ID_NAME, TABLE):
    mydb = configureMySQL()
    cursor = mydb.cursor()
    sql = "SELECT "+COLUMN + " FROM " + TABLE + " WHERE `ID_NAME` = %s"
    cursor.execute(sql, (ID_NAME,))
    result = cursor.fetchone()
    if result is not None:
        data = result[0]
        return data

    return None


def getAllFile(TABLE):
    mydb = configureMySQL()
    cursor = mydb.cursor()
    sql = "SELECT BASE64 FROM {0}".format(TABLE)
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        mydb.commit()

        base64_data_list = []
        for result in results:
            base64_data = result[0]
            base64_data_list.append(base64_data)

        return base64_data_list
    except Exception as error:
        return str(error), 500


def getCertificateDesigns(TABLE):
    mydb = configureMySQL()
    cursor = mydb.cursor()
    sql = "SELECT BASE64 FROM {0}".format(TABLE)
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        mydb.commit()

        base64_data_list = []
        for result in results:
            base64_data = result[0]
            base64_data_list.append(base64_data)

        return base64_data_list
    except Exception as error:
        return str(error), 500


# def insertCertificate(CERTIFICATE_TYPE, Client, TABLE):

#     mydb = configureMySQL()
#     cursor = mydb.cursor()
#     b = open("Templates/Images/certificates.png", "rb")
#     encoded_image = base64.b64encode(b.read()).decode('utf-8')
#     sql = "INSERT INTO {0} (`CERTIFICATE_TYPE`,`CREATED_BY`,`CLIENT_ID`,`BASE64`) VALUES (%s,%s,%s,%s)".format(
#         TABLE)
#     values = (CERTIFICATE_TYPE, admin, Client, encoded_image)

#     try:
#         cursor.execute(sql, values)
#         mydb.commit()
#         logging.info(
#             "Data inserted in table '%s' for Client with ID '%s'", TABLE, Client)
#         return True
#     except Exception as e:
#         logging.error("Failed to update data in table '%s' for Client with ID '%s'. Error: %s",
#                       TABLE, Client, str(e))
#         return False


# insertCertificate('primary', 'developindia.org', 'CERTIFICATE_DESIGNS')
