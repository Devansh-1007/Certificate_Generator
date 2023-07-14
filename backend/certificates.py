from img2pdf import convert
from tkinter import Image
from PIL import Image, ImageDraw, ImageFont
import base64
from flask import jsonify
from config import *
from awsS3 import *
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def generateCert(CERTIFICATE_NAME, CLIENT_ID):
    certificate = Image.open(baseCert_path)
    draw = ImageDraw.Draw(certificate)
    name_font = ImageFont.truetype(font_path, 75)

    w, h = draw.textsize(CERTIFICATE_NAME, name_font)
    left = (certificate.width - w) / 2
    top = 550

    draw.text((left, top), CERTIFICATE_NAME,
              fill=(75, 75, 75, 255), font=name_font)

    certificate = certificate.convert('RGB')
    folder_name = CLIENT_ID
    img_folder_path = os.path.join(allCertImgPath + '/', folder_name)
    pdf_folder_path = os.path.join(allCertPdfPath + '/', folder_name)
    if not os.path.exists(img_folder_path):
        os.makedirs(img_folder_path)
    if not os.path.exists(pdf_folder_path):
        os.makedirs(pdf_folder_path)
    eachmemberIMGpath = os.path.join(
        img_folder_path, CERTIFICATE_NAME + '.png')
    eachmemberPDFpath = os.path.join(
        pdf_folder_path, CERTIFICATE_NAME + '.pdf')
    certificate.save(eachmemberIMGpath)

    pdf_bytes = convert(eachmemberIMGpath)

    f = open(eachmemberPDFpath, "wb")
    b = open(eachmemberIMGpath, "rb")

    f.write(pdf_bytes)
    certificate.close()
    f.close()

    upload_file(eachmemberIMGpath, bucket, eachmemberIMGpath)
    upload_file(eachmemberPDFpath, bucket, eachmemberPDFpath)
    logging.info("Files uploaded for Client ID: '%s'", CLIENT_ID)

    encoded_image = base64.b64encode(b.read()).decode('utf-8')
    image = getSignedUrl(eachmemberIMGpath, bucket)
    pdf = getSignedUrl(eachmemberPDFpath, bucket)
    logging.info("Signed URLs obtained for Client ID: '%s'", CLIENT_ID)

    details = {
        "status": 'Success',
        "description": 'Certificate generated',
        "CERTIFICATE_DETAILS": {
            "CERTIFICATE_NAME": CERTIFICATE_NAME,
            "CLIENT_ID": CLIENT_ID,
            "IMAGE_URL": image,
            "PDF_URL": pdf,
            "BASE64": encoded_image
        }
    }

    logging.info("Certificate generated for Client ID: '%s'", CLIENT_ID)
    return jsonify(details)
