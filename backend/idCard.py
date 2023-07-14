from img2pdf import convert
from tkinter import Image
from PIL import Image
from flask import jsonify
from config import *
from piCodes import *
from awsS3 import *
import base64


def generateID(qr_img, ID_NAME, CLIENT_ID):

    idCard = Image.open(baseIdCard_path)
    idCard_width = idCard.width
    qr_width = qr_img.width
    boxQR = (int((idCard_width-qr_width)/2), 200)

    idCard.paste(qr_img, boxQR)
    idCard = idCard.convert('RGB')
    idCard = idCard.convert('RGB')
    idCard.paste(qr_img,  (10, 58))

    # paths -->
    folder_name = CLIENT_ID
    img_folder_path = os.path.join(allIdImgPath + '/', folder_name)
    pdf_folder_path = os.path.join(allIdPdfPath + '/', folder_name)
    if not os.path.exists(img_folder_path):
        os.makedirs(img_folder_path)
    if not os.path.exists(pdf_folder_path):
        os.makedirs(pdf_folder_path)
    eachmemberIMGpath = os.path.join(
        img_folder_path, ID_NAME + '.png')
    eachmemberPDFpath = os.path.join(
        pdf_folder_path, ID_NAME + '.pdf')
    idCard.save(eachmemberIMGpath)
    pdf_bytes = convert(eachmemberIMGpath)
    f = open(eachmemberPDFpath, "wb")
    b = open(eachmemberIMGpath, "rb")

    f.write(pdf_bytes)

    idCard.close()

    f.close()
    upload_file(eachmemberIMGpath, bucket, eachmemberIMGpath)
    upload_file(eachmemberPDFpath, bucket, eachmemberPDFpath)
    logging.info("Files uploaded for Client ID: '%s'", CLIENT_ID)
    encoded_image = base64.b64encode(b.read()).decode('utf-8')
    image = getSignedUrl(eachmemberIMGpath, bucket)
    pdf = getSignedUrl(eachmemberPDFpath, bucket)
    logging.info("Signed URLs obtained for Client ID: '%s'", CLIENT_ID)

    details = {"status": 'Success',
               "description": 'IdCard generated',
               "ID_DETAILS": {
                   "CLIENT_ID": CLIENT_ID,
                   "IMAGE_URL": image,
                   "PDF_URL": pdf,
                   "BASE64": encoded_image
               }}
    logging.info("Id generated for Client ID: '%s'", CLIENT_ID)

    return jsonify(details)
