"""
Object storage client — works with AWS S3 or any S3-compatible service
(Cloudflare R2, Backblaze B2, MinIO) via S3_ENDPOINT_URL.

Env (all optional — unset means default AWS credential chain):
    S3_ENDPOINT_URL       e.g. https://<account_id>.r2.cloudflarestorage.com
    S3_ACCESS_KEY_ID      access key (R2 API token key)
    S3_SECRET_ACCESS_KEY  secret
    S3_REGION             R2 uses "auto" (default when endpoint is set)
"""

import os
import logging

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def _client():
    endpoint = os.getenv("S3_ENDPOINT_URL")
    if endpoint:
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
            region_name=os.getenv("S3_REGION", "auto"),
        )
    return boto3.client("s3")


def _key(object_name):
    # S3 keys use forward slashes; Windows paths arrive with backslashes
    return object_name.replace("\\", "/")


def upload_file(file_name, bucket, object_name=None):
    if object_name is None:
        object_name = os.path.basename(file_name)

    try:
        _client().upload_file(file_name, bucket, _key(object_name))
        logging.info("File '%s' was uploaded to bucket '%s'", file_name, bucket)
    except ClientError as e:
        logging.error(
            "Failed to upload file '%s' to bucket '%s'. Error: %s", file_name, bucket, str(e))
        return False
    return True


def getSignedUrl(file_name, bucket):
    try:
        url = _client().generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': bucket, 'Key': _key(file_name)},
            ExpiresIn=3600,
        )
        logging.info("Got presigned URL")
    except ClientError:
        logging.exception(
            "Couldn't get a presigned URL for client method '%s'", 'get_object')
        raise
    # NOTE: the query string carries the signature — do not strip it,
    # or the URL only works on public buckets.
    return url


def downloadFile(bucket, folder_path, file_name):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    file_path = os.path.join(folder_path, file_name)
    logging.info(file_path)
    try:
        _client().download_file(bucket, _key(file_path), file_path)
        logging.info("File '%s' was downloaded from bucket '%s'", file_path, bucket)
        return True
    except ClientError as e:
        logging.error("Failed to download file '%s' from bucket '%s'. Error: %s",
                      file_path, bucket, str(e))
        return False
