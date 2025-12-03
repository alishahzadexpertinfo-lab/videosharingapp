import os
from azure.storage.blob import BlobServiceClient, ContentSettings

AZURE_STORAGE_ACCOUNT_URL = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "videosharingapp")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")

def get_blob_service_client() -> BlobServiceClient:
    # If full URL not provided, build from account name
    if AZURE_STORAGE_ACCOUNT_URL:
        account_url = AZURE_STORAGE_ACCOUNT_URL
    else:
        account_url = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
    return BlobServiceClient(account_url=account_url, credential=AZURE_STORAGE_ACCOUNT_KEY)


def upload_video_file(blob_service_client: BlobServiceClient, container_name: str, file_stream, blob_name: str, content_type: str) -> str:
    container_client = blob_service_client.get_container_client(container_name)
    try:
        container_client.create_container()
    except Exception:
        # Already exists
        pass

    blob_client = container_client.get_blob_client(blob_name)
    content_settings = ContentSettings(content_type=content_type)
    blob_client.upload_blob(file_stream, overwrite=True, content_settings=content_settings)
    # Return public URL (ensure the container or blob has appropriate access policies configured in Azure)
    return blob_client.url
