import os
from dotenv import load_dotenv
load_dotenv('Env/.env')

# Secret key for jwt
admin_secret_key = os.getenv('ADMIN_SECRET_KEY', '').encode('utf-8')
admin_iv = os.getenv('ADMIN_IV', '').encode('utf-8')
admin_content = os.getenv('ADMIN_CONTENT', '')
admin_token = os.getenv('ADMIN_TOKEN')


admin = os.getenv('ADMIN')
# Load environment variables from .env file

# Base URL
base_url = os.getenv('BASE_URL')

# MySQL credentials
mysql_host = os.getenv('MYSQL_HOST')
mysql_user = os.getenv('MYSQL_USER')
mysql_pass = os.getenv('MYSQL_PASS')
mysql_db = os.getenv('MYSQL_DB')
mysql_port = int(os.getenv('MYSQL_PORT'))

# Certificate file paths
baseCert_path = os.getenv('BASE_CERT_PATH')
baseIdCard_path = os.getenv('BASE_IDCARD_PATH')
font_path = os.getenv('FONT_PATH')

# Certificate Paths
dirpath = ''
allCertImgPath = os.getenv('ALL_CERT_IMG_PATH')
allCertPdfPath = os.getenv('ALL_CERT_PDF_PATH')

# ID Card Paths
allIdImgPath = os.getenv('ALL_ID_IMG_PATH')
allIdPdfPath = os.getenv('ALL_ID_PDF_PATH')

# S3 Bucket
bucket = os.getenv('BUCKET')
