"""Domain objects shared across routes and data handling."""


class Certificate:
    def __init__(
        self,
        CERTIFICATE_NAME,
        CERTIFICATE_IMG_PATH,
        CERTIFICATE_PDF_PATH,
        CERTIFICATE_BASE64,
    ):
        self.CERTIFICATE_NAME = CERTIFICATE_NAME
        self.CERTIFICATE_IMG_PATH = CERTIFICATE_IMG_PATH
        self.CERTIFICATE_PDF_PATH = CERTIFICATE_PDF_PATH
        self.CERTIFICATE_BASE64 = CERTIFICATE_BASE64


class IdCard:
    def __init__(self, ID_NAME, ID_IMG_PATH, ID_PDF_PATH):
        self.ID_NAME = ID_NAME
        self.ID_IMG_PATH = ID_IMG_PATH
        self.ID_PDF_PATH = ID_PDF_PATH


class Client:
    def __init__(self, CLIENT_ID, CLIENT_NAME, PASSWORD, CERTIFICATE, ID):
        self.CLIENT_ID = CLIENT_ID
        self.CLIENT_NAME = CLIENT_NAME
        self.PASSWORD = PASSWORD
        self.CERTIFICATE = CERTIFICATE
        self.ID = ID
