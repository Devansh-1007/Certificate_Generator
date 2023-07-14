from flask import Flask, request, send_file, jsonify
from config import *
from certificates import *
from idCard import *
from authentication import *
from dataHandling import *
from piCodes import *
from registerClient import *
from loginClient import *
import logging
from werkzeug.security import generate_password_hash
from flasgger import Swagger, swag_from
from flask_cors import CORS


app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.config["SWAGGER"] = {
    "title": "My API Documentation",
    "description": "This API provides endpoints for client login and certificate registration.",
    "version": "1.0.0",
    "template": {
        "info": {
            "contact": {
                "name": "Devansh Choudhary",
                "url": "https://www.linkedin.com/in/devansh-choudhary-ba68a3226/",
                "email": "choudhary.devansh1007@gmail.com"
            }
        }
    },
    "license": {
        "name": "Apache 2.0",
        "url": "http://www.apache.org/licenses/LICENSE-2.0.html"
    }
}
swagger = Swagger(app)
CORS(app)

# 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
# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class Certificate():
    def __init__(self, CERTIFICATE_NAME, CERTIFICATE_IMG_PATH, CERTIFICATE_PDF_PATH, CERTIFICATE_BASE64):
        self.CERTIFICATE_NAME = CERTIFICATE_NAME
        self.CERTIFICATE_IMG_PATH = CERTIFICATE_IMG_PATH
        self.CERTIFICATE_PDF_PATH = CERTIFICATE_PDF_PATH
        self.CERTIFICATE_BASE64 = CERTIFICATE_BASE64


class IdCard():
    def __init__(self, ID_NAME, ID_IMG_PATH, ID_PDF_PATH):
        self.ID_NAME = ID_NAME
        self.ID_IMG_PATH = ID_IMG_PATH
        self.ID_PDF_PATH = ID_PDF_PATH


class Client():
    def __init__(self, CLIENT_ID, CLIENT_NAME, PASSWORD, CERTIFICATE, ID):
        self.CLIENT_ID = CLIENT_ID
        self.CLIENT_NAME = CLIENT_NAME
        self.PASSWORD = PASSWORD
        self.CERTIFICATE = CERTIFICATE
        self.ID = ID


@ app.route('/registerClient', methods=['POST'])
@ swag_from('swagger_docs/register_client.yaml')
def register():
    data = request.get_json()
    TOKEN = request.headers.get('x-token')
    response, error_code = verifyAdmin(TOKEN)
    if response == True and error_code == 200:
        hash_password = generate_password_hash(data['PASSWORD'])
        client = Client(data['CLIENT_ID'], data['CLIENT_NAME'], hash_password,
                        'NULL', 'NULL')
        try:
            return registerClient(client)
        except Exception as error:
            return str(error), 500
    else:
        logging.info({
            "description": "Admin role required for this request.Token not verified.", "Error:%s": error_code})
        return jsonify(description="Admin role required for this request.Token not verified."), error_code


@ app.route('/loginClient', methods=['POST'])
@ swag_from('swagger_docs/login_client.yaml')
def login():

    data = request.get_json()
    CLIENT_ID = data['CLIENT_ID']
    CLIENT_NAME = data['CLIENT_NAME']
    PASSWORD = data['PASSWORD']
    try:
        return loginClient(CLIENT_ID, CLIENT_NAME, PASSWORD)
    except Exception as error:
        return str(error), 500


@ app.route('/generateCertificate', methods=['POST'])
@ swag_from('swagger_docs/generate_certificate.yaml')
def generatecert():
    try:
        data = request.get_json()
        CERTIFICATE_NAME = data['CERTIFICATE_NAME']
        CURRENT_CLIENT = request.headers.get('x-client-id')
        TOKEN = request.headers.get('x-token')
        logging.info(CURRENT_CLIENT)
        DECRYPTED_TOKEN = verifyToken(CURRENT_CLIENT, TOKEN)
        if CURRENT_CLIENT != DECRYPTED_TOKEN:
            return jsonify({"description": "Token not verified"}), 401

        try:
            checkCert = verify_Certificate(
                CERTIFICATE_NAME, CURRENT_CLIENT, 'CERTIFICATE_DETAILS')
            if checkCert:
                details = {
                    "status": 'Success',
                    "description": 'Certificate already exists',
                    "CERTIFICATE_DETAILS": {
                        "CERTIFICATE_NAME": CERTIFICATE_NAME,
                        "CREATED_BY": CURRENT_CLIENT,
                        "IMAGE_URL": getCertificateInfo('CERTIFICATE_IMG_PATH', CERTIFICATE_NAME, 'CERTIFICATE_DETAILS'),
                        "PDF_URL": getCertificateInfo('CERTIFICATE_PDF_PATH', CERTIFICATE_NAME, 'CERTIFICATE_DETAILS')
                    }
                }
                logging.info(
                    "Certificate already exists for CLIENT_ID: %s", CURRENT_CLIENT)
                return jsonify(details)
            else:
                try:
                    client = Client(CURRENT_CLIENT, 'NULL',
                                    'NULL', 'NULL', 'NULL')
                    result = generateCert(
                        CERTIFICATE_NAME, client.CLIENT_ID).json
                    client.CERTIFICATE = Certificate(
                        CERTIFICATE_NAME, 'NULL', 'NULL', 'NULL')
                    client.CERTIFICATE.CERTIFICATE_IMG_PATH = result['CERTIFICATE_DETAILS']['IMAGE_URL']
                    client.CERTIFICATE.CERTIFICATE_PDF_PATH = result['CERTIFICATE_DETAILS']['PDF_URL']
                    client.CERTIFICATE.CERTIFICATE_BASE64 = result['CERTIFICATE_DETAILS']['BASE64']
                except Exception as error:
                    return str(error), 500

                try:
                    if insertCertificate(client.CERTIFICATE, client, 'CERTIFICATE_DETAILS'):
                        return jsonify(result)
                    else:
                        return jsonify({"description": "Data cannot be inserted into the database"}), 401
                except Exception as error:
                    return jsonify({"description": "Data cannot be inserted into the database"}), 401
        except Exception as error:
            logging.error(
                "An error occurred. Certificate cannot be generated: %s", str(error))
            return str(error), 500
    except Exception as error:
        logging.error("An error occurred: %s", str(error))
        return str(error), 500


@ app.route('/generateId', methods=['POST'])
@ swag_from('swagger_docs/generate_id.yaml')
def generateId():

    try:
        data = request.get_json()
        ID_NAME = data['ID_NAME']
        CURRENT_CLIENT = request.headers.get('x-client-id')
        TOKEN = request.headers.get('x-token')
        logging.info(CURRENT_CLIENT)
        DECRYPTED_TOKEN = verifyToken(CURRENT_CLIENT, TOKEN)
        if CURRENT_CLIENT != DECRYPTED_TOKEN:
            return jsonify({"description": "Token not verified"}), 401

        try:
            checkCert = verify_ID(
                ID_NAME, CURRENT_CLIENT, 'ID_DETAILS')
            if checkCert:
                details = {
                    "status": 'Success',
                    "description": 'Id alreadys exists',
                    "ID_DETAILS": {
                        "ID_NAME": ID_NAME,
                        "CREATED_BY": CURRENT_CLIENT,
                        "IMAGE_URL": getIDInfo('ID_IMG_PATH', ID_NAME, 'ID_DETAILS'),
                        "PDF_URL": getIDInfo('ID_PDF_PATH', ID_NAME, 'ID_DETAILS')
                    }
                }
                logging.info(
                    "Id already exists for CLIENT_ID: %s", CURRENT_CLIENT)
                return jsonify(details)
            else:
                try:
                    client = Client(CURRENT_CLIENT, 'NULL',
                                    'NULL', 'NULL', 'NULL')
                    result = generateID(generateQR(client, 'ID_DETAILS'), generateBar(
                        client, 'ID_DETAILS'), ID_NAME, client.CLIENT_ID).json
                    client.ID = IdCard(
                        ID_NAME, 'NULL', 'NULL')
                    client.ID.ID_IMG_PATH = result['ID_DETAILS']['IMAGE_URL']
                    client.ID.ID_PDF_PATH = result['ID_DETAILS']['PDF_URL']
                except Exception as error:
                    return str(error), 500

                try:
                    if insertId(client.ID, client, 'ID_DETAILS'):
                        return jsonify(result)
                    else:
                        return jsonify({"description": "Data cannot be inserted into the database"}), 401
                except Exception as error:
                    return jsonify({"description": "Data cannot be inserted into the database"}), 401
        except Exception as error:
            logging.error(
                "An error occurred. Id cannot be generated: %s", str(error))
            return str(error), 500
    except Exception as error:
        logging.error("An error occurred: %s", str(error))
        return str(error), 500


@ app.route('/getCertificate', methods=['GET'])
@ swag_from('swagger_docs/get_certificate.yaml')
def getCert():
    CERTIFICATE_NAME = request.args.get('CERTIFICATE_NAME')
    EXTENSION = request.args.get('EXTENSION')
    CURRENT_CLIENT = request.headers.get('x-client-id')
    TOKEN = request.headers.get('x-token')
    logging.info(CURRENT_CLIENT)
    DECRYPTED_TOKEN = verifyToken(CURRENT_CLIENT, TOKEN)
    if CURRENT_CLIENT != DECRYPTED_TOKEN:
        return jsonify({"description": "Token not verified"}), 401
    try:
        if EXTENSION == "pdf":
            try:
                downloadFile(bucket, allCertPdfPath + '/'+CURRENT_CLIENT,
                             str(CERTIFICATE_NAME) + ".pdf")
                file = allCertPdfPath + '/'+CURRENT_CLIENT+'/' + CERTIFICATE_NAME + ".pdf"
                logging.info("File retrieved: %s", file)
                return send_file(file, mimetype='application/pdf')
            except Exception as e:
                logging.error("Failed to retrieve PDF file: %s", str(e))
                return "Failed to retrieve PDF file"
        elif EXTENSION == "img":
            try:
                downloadFile(bucket, allCertImgPath + '/'+CURRENT_CLIENT,
                             str(CERTIFICATE_NAME) + ".png")
                file = allCertImgPath + '/'+CURRENT_CLIENT + '/' + CERTIFICATE_NAME + ".png"
                logging.info("File retrieved: %s", file)
                return send_file(file, mimetype='image/gif')
            except Exception as e:
                logging.error("Failed to retrieve image file: %s", str(e))
                return "Failed to retrieve image file"
        else:
            logging.warning(
                "Invalid extension or filename: %s, %s", EXTENSION, CERTIFICATE_NAME)
            return "Invalid extension or filename"
    except Exception as e:
        logging.error("An error occurred while retrieving file: %s", str(e))
        return "File Not Found"


@ app.route('/getId', methods=['GET'])
@ swag_from('swagger_docs/get_id.yaml')
def getId():
    ID_NAME = request.args.get('ID_NAME')
    EXTENSION = request.args.get('EXTENSION')
    CURRENT_CLIENT = request.headers.get('x-client-id')
    TOKEN = request.headers.get('x-token')
    logging.info(CURRENT_CLIENT)
    DECRYPTED_TOKEN = verifyToken(CURRENT_CLIENT, TOKEN)
    if CURRENT_CLIENT != DECRYPTED_TOKEN:
        return jsonify({"description": "Token not verified"}), 401
    try:
        if EXTENSION == "pdf":
            try:
                downloadFile(bucket,  allIdPdfPath + '/' +
                             CURRENT_CLIENT, str(ID_NAME) + ".pdf")
                file = allIdPdfPath + '/'+CURRENT_CLIENT+'/' + ID_NAME + ".pdf"
                logging.info("File retrieved: %s", file)
                return send_file(file, mimetype='application/pdf')
            except Exception as e:
                logging.error("Failed to retrieve PDF file: %s", str(e))
                return "Failed to retrieve PDF file"
        elif EXTENSION == "img":
            try:
                downloadFile(bucket, allIdImgPath + '/' +
                             CURRENT_CLIENT, str(ID_NAME) + ".png")
                file = allIdImgPath + '/'+CURRENT_CLIENT + '/' + ID_NAME + ".png"
                logging.info("File retrieved: %s", file)
                return send_file(file, mimetype='image/gif')
            except Exception as e:
                logging.error("Failed to retrieve image file: %s", str(e))
                return "Failed to retrieve image file"
        else:
            logging.warning(
                "Invalid extension or filename: %s, %s", EXTENSION, ID_NAME)
            return "Invalid extension or filename"
    except Exception as e:
        logging.error("An error occurred while retrieving file: %s", str(e))
        return "File Not Found"


@app.route('/getAllCertificate', methods=['GET'])
@ swag_from('swagger_docs/get_AllCertificate.yaml')
def getAllCert():
    CURRENT_CLIENT = request.headers.get('x-client-id')
    TOKEN = request.headers.get('x-token')
    logging.info(CURRENT_CLIENT)
    DECRYPTED_TOKEN = verifyToken(CURRENT_CLIENT, TOKEN)
    if CURRENT_CLIENT != DECRYPTED_TOKEN:
        return jsonify({"description": "Token not verified"}), 401
    try:
        # Provide the appropriate table name
        base64_data_list = getAllFile('CERTIFICATE_DETAILS')
        return jsonify({"base64_data_list": base64_data_list})
    except Exception as error:
        return jsonify({"description": "Failed to retrieve files", "error": str(error)}), 500


@app.route('/getAllId', methods=['GET'])
@ swag_from('swagger_docs/get_AllId.yaml')
def getAllId():
    CURRENT_CLIENT = request.headers.get('x-client-id')
    TOKEN = request.headers.get('x-token')
    logging.info(CURRENT_CLIENT)
    DECRYPTED_TOKEN = verifyToken(CURRENT_CLIENT, TOKEN)
    if CURRENT_CLIENT != DECRYPTED_TOKEN:
        return jsonify({"description": "Token not verified"}), 401
    try:
        # Provide the appropriate table name
        base64_data_list = getAllFile('ID_DETAILS')
        return jsonify({"base64_data_list": base64_data_list})
    except Exception as error:
        return jsonify({"description": "Failed to retrieve files", "error": str(error)}), 500


@app.route('/getCertificateDesigns', methods=['GET'])
def getCertDesign():
    CURRENT_CLIENT = request.headers.get('x-client-id')
    TOKEN = request.headers.get('x-token')
    logging.info(CURRENT_CLIENT)
    DECRYPTED_TOKEN = verifyToken(CURRENT_CLIENT, TOKEN)
    if CURRENT_CLIENT != DECRYPTED_TOKEN:
        return jsonify({"description": "Token not verified"}), 401
    try:
        base64_data_list = getCertificateDesigns('CERTIFICATE_DESIGNS')
        return jsonify({"base64_data_list": base64_data_list})
    except Exception as error:
        return jsonify({"description": "Failed to retrieve files", "error": str(error)}), 500


if __name__ == '__main__':
    app.run(debug=True)
