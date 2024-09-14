import logging
import boto3
from botocore.exceptions import ClientError
from urllib.parse import urlsplit, urlunsplit
import os

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def upload_file(file_name, bucket, object_name=None):
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
        logging.info("File '%s' was uploaded to bucket '%s'",
                     file_name, bucket)
    except ClientError as e:
        logging.error(
            "Failed to upload file '%s' to bucket '%s'. Error: %s", file_name, bucket, str(e))
        return False
    return True


def getSignedUrl(file_name, bucket):
    s3_client = boto3.client('s3')
    try:
        url = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': bucket, 'Key': file_name},
            ExpiresIn=3600
        )
        parsed_url = urlsplit(url)
        trimmed_url = urlunsplit(
            (parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', ''))
        logging.info("Got presigned URL")
    except ClientError:
        logging.exception(
            "Couldn't get a presigned URL for client method '%s'", 'get_object')
        raise
    return trimmed_url


def downloadFile(bucket, folder_path, file_name):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    file_path = os.path.join(folder_path, file_name)
    object_name = file_path
    logging.info(file_path)
    s3 = boto3.client('s3')
    try:
        s3.download_file(bucket, object_name, file_path)
        logging.info("File '%s' was downloaded from bucket '%s'",
                     object_name, bucket)
        return True
    except ClientError as e:
        logging.error("Failed to download file '%s' from bucket '%s' where filename = %s. Error: %s",
                      object_name, bucket, file_path, str(e))
        return False


