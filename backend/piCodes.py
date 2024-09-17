from PIL import Image
from io import BytesIO
from barcode.codex import Gs1_128
from barcode.writer import ImageWriter
import qrcode
import logging
from dataHandling import *
import io


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def generateQR(Client, TABLE):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=2,
        border=4,
    )
    img_url = getIDInfo("ID_IMG_PATH", Client.CLIENT_ID, TABLE)
    pdf_url = getIDInfo("ID_PDF_PATH", Client.CLIENT_ID, TABLE)
    data = {
        "CLIENT_ID": Client.CLIENT_ID,
        "CLIENT_NAME": Client.CLIENT_NAME,
        "CERTIFICATE_DETAILS": {
            "CLIENT_ID": Client.CLIENT_ID,
            "IMAGE_URL": img_url,
            "PDF_URL": pdf_url,
        },
    }
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert the qrcode image to a PIL Image object
    pil_img = img.get_image()

    # Create a BytesIO object to hold the image data
    img_buffer = BytesIO()

    # Save the PIL Image to the buffer in PNG format
    pil_img.save(img_buffer, format="PNG")

    # Rewind the buffer to the beginning
    img_buffer.seek(0)

    # Create a new PIL Image object from the buffer
    pil_image = Image.open(img_buffer)

    # Log success message
    logging.info("QR code generated for Client: {}".format(Client.CLIENT_ID))

    return pil_image


def generateBar(Client, TABLE):
    img_url = getIDInfo("ID_IMG_PATH", Client.CLIENT_ID, TABLE)
    pdf_url = getIDInfo("ID_PDF_PATH", Client.CLIENT_ID, TABLE)
    data = {Client.CLIENT_ID, Client.CLIENT_NAME, img_url, pdf_url}

    barcode_data = io.BytesIO()

    try:
        Gs1_128(str(data), writer=ImageWriter()).write(barcode_data)
        barcode_data.seek(0)

        # Log success message
        logging.info("Barcode generated for Client: {}".format(Client.CLIENT_ID))

        return barcode_data

    except Exception as e:
        # Log error message
        logging.error(
            "Failed to generate barcode for Client: {}. Error: {}".format(
                Client.CLIENT_ID, str(e)
            )
        )
        raise
