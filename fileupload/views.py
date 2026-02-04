"""
File Upload Views

This module contains API endpoints for uploading files to Azure Blob Storage.
All endpoints require MSAL OAuth authentication.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from .azure_storage import AzureBlobStorageService


class FileUploadView(APIView):
    """
    API endpoint for uploading files to Azure Blob Storage.
    
    POST /api/upload/
    - Accepts multipart/form-data with file field
    - Requires valid OAuth Bearer token
    - Uploads file to Azure Blob Storage using managed identity
    - Returns blob URL and metadata
    """
    
    def post(self, request):
        """Handle file upload requests."""
        # Check if file is present in request
        if 'file' not in request.FILES:
            return Response({
                'error': 'No file provided',
                'message': 'Please include a file in the request with key "file"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        
        # Validate file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        if file.size > max_size:
            return Response({
                'error': 'File too large',
                'message': f'File size exceeds maximum allowed size of {max_size / (1024*1024)}MB'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user info from request (set by middleware)
        user_id = getattr(request, 'user_info', {}).get('user_id', 'anonymous')
        
        try:
            # Initialize Azure Blob Storage service
            storage_service = AzureBlobStorageService()
            
            # Upload file
            result = storage_service.upload_file(
                file=file,
                user_id=user_id
            )
            
            return Response({
                'message': 'File uploaded successfully',
                'data': result
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({
                'error': 'Configuration error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({
                'error': 'Upload failed',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileListView(APIView):
    """
    API endpoint for listing uploaded files.
    
    GET /api/files/
    - Requires valid OAuth Bearer token
    - Returns list of files uploaded by the authenticated user
    """
    
    def get(self, request):
        """Handle file list requests."""
        # Get user info from request (set by middleware)
        user_id = getattr(request, 'user_info', {}).get('user_id', 'anonymous')
        
        try:
            # Initialize Azure Blob Storage service
            storage_service = AzureBlobStorageService()
            
            # List files for user
            blobs = storage_service.list_blobs(user_id=user_id)
            
            return Response({
                'message': 'Files retrieved successfully',
                'count': len(blobs),
                'data': blobs
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'error': 'Configuration error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({
                'error': 'Failed to retrieve files',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HealthCheckView(APIView):
    """
    Health check endpoint (no authentication required).
    
    GET /api/health/
    - Returns application health status
    - Does not require authentication
    """
    
    def get(self, request):
        """Handle health check requests."""
        return Response({
            'status': 'healthy',
            'message': 'File upload service is running'
        }, status=status.HTTP_200_OK)

