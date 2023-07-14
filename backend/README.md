# Flask Project - Certificate and ID Card Generation API

This Flask project provides a RESTful API for generating certificates and ID cards, registering clients, and authenticating users. It offers a convenient way to manage certificate and ID card generation processes and allows clients to securely access and retrieve their generated documents.

## Project Structure and Files

The project is structured as follows:

- **config.py**: This file contains configuration settings for the project, such as database connection details and file paths.
- **certificates.py**: This module handles the generation and retrieval of certificates.
- **idCard.py**: This module handles the generation and retrieval of ID cards.
- **authentication.py**: This module provides functions for user authentication and token generation.
- **dataHandling.py**: This module handles the insertion and retrieval of data from the database.
- **piCodes.py**: This module contains functions for generating QR codes and barcodes.
- **registerClient.py**: This module handles the registration of clients.
- **loginClient.py**: This module handles client login and authentication.
- **app.py**: This is the main application file that defines the Flask routes and API endpoints.


## Environment Variables

# MySQL credentials

MYSQL_HOST

MYSQL_USER

MYSQL_PASS

MYSQL_DB

MYSQL_PORT

# Certificate file paths

BASE_CERT_PATH

BASE_IDCARD_PATH

FONT_PATH

# Certificate Paths

ALL_CERT_PATH

ALL_CERT_IMG_PATH

ALL_CERT_PDF_PATH

# ID Card Paths

ALL_ID_PATH

ALL_ID_IMG_PATH=${ALL_ID_PATH}/Images

ALL_ID_PDF_PATH=${ALL_ID_PATH}/PDFs

# S3 Bucket

BUCKET

## .env file path

ENV_FILEPATH 

# API Endpoints

The project exposes the following API endpoints:

- **POST /registerClient**: This endpoint allows clients to register by providing their client ID, client name, and password. The client information is securely stored in the database.
- **POST /loginClient**: Clients can use this endpoint to authenticate themselves by providing their client ID, client name, and password. Upon successful authentication, a token is generated and returned to the client.
- **POST /generateCertificate**: This endpoint generates a certificate for the authenticated client. The client must provide the desired certificate name. The certificate image and PDF paths are stored in the database.
- **POST /generateId**: This endpoint generates an ID card for the authenticated client. The client must provide the desired ID card name. The ID card image and PDF paths are stored in the database.
- **GET /getCertificate**: Clients can use this endpoint to retrieve a certificate file (PDF or image) by specifying the certificate name and file extension.
- **GET /getId**: Clients can use this endpoint to retrieve an ID card file (PDF or image) by specifying the ID card name and file extension.

## Dependencies and Setup

To run the Flask project, make sure you have the following dependencies installed:

- Flask
- Flasgger
- Werkzeug
- bcrypt
- Other dependencies specified in the `requirements.txt` file.

You can install the dependencies using the following command:

```shell
$ pip install -r requirements.txt
```

## Usage

To run the application, execute the `main.py` file. The application will run in debug mode, allowing for convenient development and testing.

```shell
$ python main.py
```

Make sure to configure the necessary settings in the `config.py` file, such as the database connection details and file paths.

## Conclusion

This Flask project provides a robust API for generating certificates and ID cards, registering clients, and handling user authentication. It follows a modular structure, separating different functionalities into separate modules. The API endpoints allow clients to interact with the system securely and retrieve their generated documents. With proper configuration and setup, this project can be easily extended and integrated into larger applications or systems requiring certificate and ID card generation capabilities.
