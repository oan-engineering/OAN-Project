#!/usr/bin/env python3
import os
import sys
from minio import Minio

def main():
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9022")
    access_key = os.getenv("MINIO_ACCESS_KEY", "admin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "adminsecret")
    bucket_name = "documents"

    print(f"Connecting to MinIO at {endpoint}...")
    client = Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=False
    )

    if not client.bucket_exists(bucket_name):
        print(f"Creating bucket '{bucket_name}'...")
        client.make_bucket(bucket_name)

    images_dir = "/home/rithikharavi/Music/Gen2- crop-registry/cropsown-regsitry/docker/db-seed/sample-data/images"
    image_files = ["farmer_01.jpg", "farmer_02.jpg", "farmer_03.jpg"]

    for filename in image_files:
        filepath = os.path.join(images_dir, filename)
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue
        print(f"Uploading {filename} to bucket '{bucket_name}' via S3 API...")
        client.fput_object(
            bucket_name,
            filename,
            filepath,
            content_type="image/jpeg"
        )
        print(f"Successfully uploaded {filename}")

    print("All images uploaded to MinIO documents bucket.")

if __name__ == "__main__":
    main()
