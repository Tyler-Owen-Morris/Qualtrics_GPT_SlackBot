import os
import boto3
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)


def upload_folder_to_s3(bucket_name, s3_folder_path, local_folder_path):
    s3_client = boto3.client(
        's3', aws_access_key_id=os.environ['AWS_ACCESS_KEY'], aws_secret_access_key=os.environ['AWS_SECRET_KEY'])
    for root, dirs, files in os.walk(local_folder_path):
        for filename in files:
            # construct the full local path
            local_path = os.path.join(root, filename)
            # construct the full S3 path
            relative_path = os.path.relpath(local_path, local_folder_path)
            s3_path = os.path.join(s3_folder_path, relative_path)

            # current time stamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            s3_archive_path = f"{s3_path}"

            # upload the file
            s3_client.upload_file(local_path, bucket_name, s3_archive_path)
            print(
                f'File {filename} uploaded to {bucket_name}/{s3_archive_path}')
