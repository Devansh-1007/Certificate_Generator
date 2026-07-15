"""
ID-card generation — rendered through the template engine (replaces the legacy
QR-paste onto idCard.png; the base image / barcode path was broken).
"""

import os
import json
import base64
import logging
import datetime

from flask import jsonify
from img2pdf import convert

from config import bucket, allIdImgPath, allIdPdfPath, base_url
from awsS3 import upload_file, getSignedUrl
from templateEngine import render_template

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

_PRESET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "templateEngine", "presets", "default_id_card.json")


def generateID(ID_NAME, CLIENT_ID, ORG_NAME=None):
    try:
        with open(_PRESET) as f:
            template = json.load(f)

        data = {
            "HOLDER_NAME": ID_NAME,
            "CLIENT_ID": CLIENT_ID,
            "ORG_NAME": ORG_NAME or CLIENT_ID.upper(),
            "ISSUE_DATE": datetime.date.today().strftime("%d %B %Y"),
            "QR_DATA": "{}/verify/{}/{}".format(base_url or "http://localhost:5000",
                                                CLIENT_ID, ID_NAME.replace(" ", "-")),
        }
        image = render_template(template, data)

        img_folder = os.path.join(allIdImgPath, CLIENT_ID)
        pdf_folder = os.path.join(allIdPdfPath, CLIENT_ID)
        os.makedirs(img_folder, exist_ok=True)
        os.makedirs(pdf_folder, exist_ok=True)
        img_path = os.path.join(img_folder, ID_NAME + ".png")
        pdf_path = os.path.join(pdf_folder, ID_NAME + ".pdf")
        image.save(img_path)
        with open(pdf_path, "wb") as f:
            f.write(convert(img_path))

        image_url = pdf_url = None
        try:
            upload_file(img_path, bucket, img_path)
            upload_file(pdf_path, bucket, pdf_path)
            image_url = getSignedUrl(img_path, bucket)
            pdf_url = getSignedUrl(pdf_path, bucket)
        except Exception as e:
            logging.warning("Object storage unavailable (%s) — serving local copy", str(e))

        with open(img_path, "rb") as b:
            encoded = base64.b64encode(b.read()).decode("utf-8")

        return jsonify({
            "status": "Success",
            "description": "Id generated",
            "ID_DETAILS": {
                "ID_NAME": ID_NAME,
                "CLIENT_ID": CLIENT_ID,
                "IMAGE_URL": image_url,
                "PDF_URL": pdf_url,
                "BASE64": encoded,
            },
        })
    except Exception as e:
        logging.error("Error generating ID for Client '%s': %s", CLIENT_ID, str(e))
        return jsonify({"status": "Error", "description": "Id generation failed: " + str(e)})
