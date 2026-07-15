"""
Certificate generation — renders through the schema-driven template engine
(replaces the legacy fixed-coordinate PIL drawing on certificates.png).
"""

import os
import json
import base64
import logging
import datetime

from flask import jsonify
from img2pdf import convert

from config import bucket, allCertImgPath, allCertPdfPath, base_url
from awsS3 import upload_file, getSignedUrl
from templateEngine import render_template, extract_placeholders

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

_PRESET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "templateEngine", "presets", "default_certificate.json")


def default_template():
    with open(_PRESET) as f:
        return json.load(f)


def build_data(template, RECIPIENT_NAME, CLIENT_ID, overrides=None):
    """Fill every placeholder the template uses: request overrides > defaults."""
    overrides = overrides or {}
    defaults = {
        "RECIPIENT_NAME": RECIPIENT_NAME,
        "EVENT_NAME": "Outstanding Achievement",
        "ISSUE_DATE": datetime.date.today().strftime("%d %B %Y"),
        "SIGNATORY_NAME": CLIENT_ID,
        "SIGNATORY_TITLE": "Authorized Signatory",
        "VERIFY_URL": "{}/verify/{}/{}".format(base_url or "http://localhost:5000",
                                               CLIENT_ID, RECIPIENT_NAME.replace(" ", "-")),
    }
    data = {}
    for name in extract_placeholders(template):
        data[name] = overrides.get(name) or defaults.get(name) or name.replace("_", " ").title()
    data["RECIPIENT_NAME"] = RECIPIENT_NAME
    return data


def generateCert(CERTIFICATE_NAME, CLIENT_ID, template=None, overrides=None):
    try:
        template = template or default_template()
        image = render_template(template, build_data(template, CERTIFICATE_NAME, CLIENT_ID, overrides))

        img_folder_path = os.path.join(allCertImgPath, CLIENT_ID)
        pdf_folder_path = os.path.join(allCertPdfPath, CLIENT_ID)
        os.makedirs(img_folder_path, exist_ok=True)
        os.makedirs(pdf_folder_path, exist_ok=True)
        img_path = os.path.join(img_folder_path, CERTIFICATE_NAME + ".png")
        pdf_path = os.path.join(pdf_folder_path, CERTIFICATE_NAME + ".pdf")

        image.save(img_path)
        with open(pdf_path, "wb") as f:
            f.write(convert(img_path))

        image_url = pdf_url = None
        try:
            upload_file(img_path, bucket, img_path)
            upload_file(pdf_path, bucket, pdf_path)
            image_url = getSignedUrl(img_path, bucket)
            pdf_url = getSignedUrl(pdf_path, bucket)
            logging.info("Files uploaded for Client ID: '%s'", CLIENT_ID)
        except Exception as e:
            # storage optional in local dev — the certificate still exists on disk
            logging.warning("Object storage unavailable (%s) — serving local copy", str(e))

        with open(img_path, "rb") as b:
            encoded_image = base64.b64encode(b.read()).decode("utf-8")

        details = {
            "status": "Success",
            "description": "Certificate generated",
            "CERTIFICATE_DETAILS": {
                "CERTIFICATE_NAME": CERTIFICATE_NAME,
                "CLIENT_ID": CLIENT_ID,
                "TEMPLATE": template.get("name"),
                "IMAGE_URL": image_url,
                "PDF_URL": pdf_url,
                "BASE64": encoded_image,
            },
        }
        logging.info("Certificate generated for Client ID: '%s'", CLIENT_ID)
        return jsonify(details)
    except Exception as e:
        logging.error("Error generating certificate for Client ID '%s': %s", CLIENT_ID, str(e))
        return jsonify({"status": "Error", "description": "Certificate generation failed: " + str(e)})
