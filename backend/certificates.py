import os
import logging
from flask import jsonify
from PIL import Image, ImageDraw, ImageFont
import base64
from img2pdf import convert
from config import *
from awsS3 import *

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def generateCert(CERTIFICATE_NAME, CLIENT_ID):
    try:
        certificate = Image.open(baseCert_path)
        draw = ImageDraw.Draw(certificate)
        name_font = ImageFont.truetype(font=font_path, size=75)
        print(name_font)
        w = draw.textlength(CERTIFICATE_NAME, font=name_font)
        left = (certificate.width - w) / 2
        top = 550

        draw.text((left, top), CERTIFICATE_NAME, fill=(75, 75, 75, 255), font=name_font)

        certificate = certificate.convert("RGB")
        folder_name = CLIENT_ID
        img_folder_path = os.path.join(allCertImgPath, folder_name)
        pdf_folder_path = os.path.join(allCertPdfPath, folder_name)
        os.makedirs(img_folder_path, exist_ok=True)
        os.makedirs(pdf_folder_path, exist_ok=True)
        eachmemberIMGpath = os.path.join(img_folder_path, CERTIFICATE_NAME + ".png")
        eachmemberPDFpath = os.path.join(pdf_folder_path, CERTIFICATE_NAME + ".pdf")
        certificate.save(eachmemberIMGpath)
        pdf_bytes = convert(eachmemberIMGpath)
        with open(eachmemberPDFpath, "wb") as f:
            f.write(pdf_bytes)

        with open(eachmemberIMGpath, "rb") as b:
            upload_file(eachmemberIMGpath, bucket, eachmemberIMGpath)
            upload_file(eachmemberPDFpath, bucket, eachmemberPDFpath)
            logging.info("Files uploaded for Client ID: '%s'", CLIENT_ID)

            encoded_image = base64.b64encode(b.read()).decode("utf-8")
            image = getSignedUrl(eachmemberIMGpath, bucket)
            pdf = getSignedUrl(eachmemberPDFpath, bucket)
            logging.info("Signed URLs obtained for Client ID: '%s'", CLIENT_ID)

            details = {
                "status": "Success",
                "description": "Certificate generated",
                "CERTIFICATE_DETAILS": {
                    "CERTIFICATE_NAME": CERTIFICATE_NAME,
                    "CLIENT_ID": CLIENT_ID,
                    "IMAGE_URL": image,
                    "PDF_URL": pdf,
                    "BASE64": encoded_image,
                },
            }

            logging.info("Certificate generated for Client ID: '%s'", CLIENT_ID)
            return jsonify(details)
    except Exception as e:
        logging.error(
            "Error generating certificate for Client ID '%s': %s", CLIENT_ID, str(e)
        )
        return jsonify(
            {"status": "Error", "description": "Certificate generation failed"}
        )
