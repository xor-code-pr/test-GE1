"""
Azure Blob Storage Service

This service handles file uploads to Azure Blob Storage using managed identity authentication.
"""
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from django.conf import settings
import uuid
from datetime import datetime


class AzureBlobStorageService:
    """
    Service for uploading files to Azure Blob Storage using managed identity.
    
    This service uses DefaultAzureCredential which automatically handles:
    - Managed Identity (for Azure-hosted applications)
    - Azure CLI credentials (for local development)
    - Environment variables
    - Interactive browser authentication
    """
    
    def __init__(self):
        """Initialize the blob service client with managed identity."""
        self.account_name = settings.AZURE_STORAGE_ACCOUNT_NAME
        self.container_name = settings.AZURE_STORAGE_CONTAINER_NAME
        
        if not self.account_name:
            raise ValueError("AZURE_STORAGE_ACCOUNT_NAME must be configured")
        
        # Create blob service client using managed identity
        account_url = f"https://{self.account_name}.blob.core.windows.net"
        credential = DefaultAzureCredential()
        self.blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=credential
        )
        
    def upload_file(self, file, filename=None, user_id=None):
        """
        Upload a file to Azure Blob Storage.
        
        Args:
            file: The file object to upload (from request.FILES)
            filename: Optional custom filename. If not provided, uses original name
            user_id: Optional user identifier to organize files by user
            
        Returns:
            dict: Contains blob_url, blob_name, and other metadata
            
        Raises:
            Exception: If upload fails
        """
        try:
            # Generate unique blob name
            original_filename = filename or file.name
            file_extension = original_filename.split('.')[-1] if '.' in original_filename else ''
            unique_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            
            # Construct blob name with user organization if provided
            if user_id:
                blob_name = f"{user_id}/{timestamp}_{unique_id}.{file_extension}"
            else:
                blob_name = f"{timestamp}_{unique_id}.{file_extension}"
            
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Upload file
            file.seek(0)  # Reset file pointer to beginning
            blob_client.upload_blob(file.read(), overwrite=True)
            
            # Get blob URL
            blob_url = blob_client.url
            
            return {
                'success': True,
                'blob_name': blob_name,
                'blob_url': blob_url,
                'original_filename': original_filename,
                'size': file.size,
                'content_type': file.content_type,
                'uploaded_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Failed to upload file to Azure Blob Storage: {str(e)}")
    
    def list_blobs(self, user_id=None):
        """
        List blobs in the container, optionally filtered by user_id.
        
        Args:
            user_id: Optional user identifier to filter blobs
            
        Returns:
            list: List of blob metadata dictionaries
        """
        try:
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            
            blobs = []
            blob_list = container_client.list_blobs()
            
            for blob in blob_list:
                # Filter by user_id if provided
                if user_id and not blob.name.startswith(f"{user_id}/"):
                    continue
                    
                blobs.append({
                    'name': blob.name,
                    'size': blob.size,
                    'created_on': blob.creation_time.isoformat() if blob.creation_time else None,
                    'last_modified': blob.last_modified.isoformat() if blob.last_modified else None,
                    'content_type': blob.content_settings.content_type if blob.content_settings else None,
                })
            
            return blobs
            
        except Exception as e:
            raise Exception(f"Failed to list blobs: {str(e)}")
