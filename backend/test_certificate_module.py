import unittest
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO
from flask import jsonify
import base64
from PIL import Image

# Assuming the generateCert function is inside a module called 'certificate_module'
from certificates import generateCert


class TestGenerateCert(unittest.TestCase):
    @patch("certificates.upload_file")
    @patch("certificates.getSignedUrl")
    @patch("certificates.convert")
    @patch("certificates.os.makedirs")
    @patch("certificates.Image.open")
    @patch("certificates.ImageFont.truetype")
    def test_generateCert(
        self,
        mock_truetype,
        mock_open_img,
        mock_makedirs,
        mock_convert,
        mock_getSignedUrl,
        mock_upload_file,
    ):
        # Mock the image and font loading
        mock_img = MagicMock(spec=Image.Image)
        mock_open_img.return_value = mock_img

        mock_font = MagicMock()
        mock_truetype.return_value = mock_font

        # Mock conversion to PDF bytes
        mock_convert.return_value = b"fake-pdf-bytes"

        # Mock the os.makedirs to avoid creating actual directories
        mock_makedirs.return_value = None

        # Mock upload_file function for S3 upload
        mock_upload_file.return_value = None

        # Mock getSignedUrl to return fake URLs
        mock_getSignedUrl.side_effect = [
            "http://fakeimageurl.com",
            "http://fakepdfurl.com",
        ]

        # Mock Image save and other operations
        mock_img.save.return_value = None

        # Mock file read operation for base64 encoding
        with patch(
            "builtins.open", mock_open(read_data=b"fake-image-bytes")
        ) as mock_file:
            CERTIFICATE_NAME = "John Doe"
            CLIENT_ID = "12345"

            # Call the generateCert function
            response = generateCert(CERTIFICATE_NAME, CLIENT_ID)

            # Ensure the response is a JSON object with expected structure
            self.assertIn("CERTIFICATE_DETAILS", response.json)
            self.assertEqual(
                response.json["CERTIFICATE_DETAILS"]["CERTIFICATE_NAME"],
                CERTIFICATE_NAME,
            )
            self.assertEqual(
                response.json["CERTIFICATE_DETAILS"]["CLIENT_ID"], CLIENT_ID
            )
            self.assertEqual(
                response.json["CERTIFICATE_DETAILS"]["IMAGE_URL"],
                "http://fakeimageurl.com",
            )
            self.assertEqual(
                response.json["CERTIFICATE_DETAILS"]["PDF_URL"], "http://fakepdfurl.com"
            )

            # Ensure the upload function was called twice (once for image, once for PDF)
            self.assertEqual(mock_upload_file.call_count, 2)

            # Ensure the signed URL function was called twice
            self.assertEqual(mock_getSignedUrl.call_count, 2)


if __name__ == "__main__":
    unittest.main()
