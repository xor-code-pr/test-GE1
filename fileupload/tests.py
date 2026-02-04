"""
Unit tests for the file upload application.

Tests cover:
- MSAL OAuth authentication middleware
- Azure Blob Storage service
- File upload views
- File list views
- Health check endpoint
"""
from django.test import TestCase, RequestFactory, Client
from django.http import JsonResponse
from django.conf import settings
from unittest.mock import Mock, patch, MagicMock
import jwt
import json
from datetime import datetime, timedelta, timezone
import io

from .middleware import MSALAuthMiddleware
from .views import FileUploadView, FileListView, HealthCheckView
from .azure_storage import AzureBlobStorageService


class MSALAuthMiddlewareTests(TestCase):
    """Test cases for MSAL authentication middleware."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        # Use a simple lambda instead of Mock to avoid interference
        self.get_response = lambda request: JsonResponse({'success': True})
        self.middleware = MSALAuthMiddleware(self.get_response)
    
    def test_public_path_allows_no_auth(self):
        """Test that public paths don't require authentication."""
        request = self.factory.get('/api/health/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['success'], True)
    
    def test_admin_path_allows_no_auth(self):
        """Test that admin paths don't require authentication."""
        request = self.factory.get('/admin/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['success'], True)
    
    def test_missing_authorization_header(self):
        """Test that missing Authorization header returns 401."""
        request = self.factory.post('/api/upload/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Missing or invalid Authorization header')
    
    def test_invalid_authorization_format(self):
        """Test that invalid Authorization format returns 401."""
        request = self.factory.post('/api/upload/')
        request.META['HTTP_AUTHORIZATION'] = 'InvalidFormat token123'
        response = self.middleware(request)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_valid_token_sets_user_info(self):
        """Test that valid token sets user info in request."""
        # Create a valid token
        payload = {
            'oid': 'user-123',
            'preferred_username': 'test@example.com',
            'name': 'Test User',
            'exp': (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
            'iat': datetime.now(timezone.utc).timestamp()
        }
        token = jwt.encode(payload, 'secret', algorithm='HS256')
        
        request = self.factory.post('/api/upload/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        response = self.middleware(request)
        
        # Check that the response is successful (middleware passed through)
        self.assertEqual(response.status_code, 200)
        
        # Check that user info was set
        self.assertTrue(hasattr(request, 'user_info'))
        self.assertEqual(request.user_info['user_id'], 'user-123')
        self.assertEqual(request.user_info['email'], 'test@example.com')
        self.assertEqual(request.user_info['name'], 'Test User')
        self.assertTrue(request.token_validated)
    
    def test_expired_token_returns_401(self):
        """Test that expired token returns 401."""
        payload = {
            'oid': 'user-123',
            'exp': (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp(),
        }
        token = jwt.encode(payload, 'secret', algorithm='HS256')
        
        request = self.factory.post('/api/upload/')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        with patch('fileupload.middleware.jwt.decode', side_effect=jwt.ExpiredSignatureError):
            response = self.middleware(request)
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Token expired')
    
    def test_invalid_token_returns_401(self):
        """Test that invalid token returns 401."""
        request = self.factory.post('/api/upload/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer invalid.token.here'
        
        response = self.middleware(request)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertIn('error', data)


class AzureBlobStorageServiceTests(TestCase):
    """Test cases for Azure Blob Storage service."""
    
    @patch('fileupload.azure_storage.BlobServiceClient')
    @patch('fileupload.azure_storage.DefaultAzureCredential')
    def test_init_with_account_name(self, mock_credential, mock_blob_client):
        """Test service initialization with account name."""
        with self.settings(AZURE_STORAGE_ACCOUNT_NAME='testaccount'):
            service = AzureBlobStorageService()
            self.assertEqual(service.account_name, 'testaccount')
            mock_credential.assert_called_once()
            mock_blob_client.assert_called_once()
    
    def test_init_without_account_name_raises_error(self):
        """Test that missing account name raises ValueError."""
        with self.settings(AZURE_STORAGE_ACCOUNT_NAME=''):
            with self.assertRaises(ValueError) as context:
                AzureBlobStorageService()
            self.assertIn('AZURE_STORAGE_ACCOUNT_NAME', str(context.exception))
    
    @patch('fileupload.azure_storage.BlobServiceClient')
    @patch('fileupload.azure_storage.DefaultAzureCredential')
    def test_upload_file_success(self, mock_credential, mock_blob_client):
        """Test successful file upload."""
        # Mock blob client
        mock_blob = MagicMock()
        mock_blob.url = 'https://testaccount.blob.core.windows.net/uploads/test.txt'
        mock_blob_client.return_value.get_blob_client.return_value = mock_blob
        
        with self.settings(AZURE_STORAGE_ACCOUNT_NAME='testaccount'):
            service = AzureBlobStorageService()
            
            # Create mock file
            mock_file = MagicMock()
            mock_file.name = 'test.txt'
            mock_file.size = 1024
            mock_file.content_type = 'text/plain'
            mock_file.read.return_value = b'test content'
            mock_file.seek = MagicMock()
            
            result = service.upload_file(mock_file, user_id='user-123')
            
            # Verify result
            self.assertTrue(result['success'])
            self.assertIn('blob_name', result)
            self.assertIn('blob_url', result)
            self.assertEqual(result['original_filename'], 'test.txt')
            self.assertEqual(result['size'], 1024)
            self.assertEqual(result['content_type'], 'text/plain')
            
            # Verify blob upload was called
            mock_blob.upload_blob.assert_called_once()
    
    @patch('fileupload.azure_storage.BlobServiceClient')
    @patch('fileupload.azure_storage.DefaultAzureCredential')
    def test_upload_file_with_custom_filename(self, mock_credential, mock_blob_client):
        """Test file upload with custom filename."""
        mock_blob = MagicMock()
        mock_blob.url = 'https://testaccount.blob.core.windows.net/uploads/custom.txt'
        mock_blob_client.return_value.get_blob_client.return_value = mock_blob
        
        with self.settings(AZURE_STORAGE_ACCOUNT_NAME='testaccount'):
            service = AzureBlobStorageService()
            
            mock_file = MagicMock()
            mock_file.name = 'original.txt'
            mock_file.size = 512
            mock_file.content_type = 'text/plain'
            mock_file.read.return_value = b'content'
            mock_file.seek = MagicMock()
            
            result = service.upload_file(mock_file, filename='custom.txt')
            
            self.assertEqual(result['original_filename'], 'custom.txt')
    
    @patch('fileupload.azure_storage.BlobServiceClient')
    @patch('fileupload.azure_storage.DefaultAzureCredential')
    def test_upload_file_failure(self, mock_credential, mock_blob_client):
        """Test file upload failure handling."""
        mock_blob_client.return_value.get_blob_client.side_effect = Exception('Upload failed')
        
        with self.settings(AZURE_STORAGE_ACCOUNT_NAME='testaccount'):
            service = AzureBlobStorageService()
            
            mock_file = MagicMock()
            mock_file.name = 'test.txt'
            
            with self.assertRaises(Exception) as context:
                service.upload_file(mock_file)
            
            self.assertIn('Failed to upload file', str(context.exception))
    
    @patch('fileupload.azure_storage.BlobServiceClient')
    @patch('fileupload.azure_storage.DefaultAzureCredential')
    def test_list_blobs_success(self, mock_credential, mock_blob_client):
        """Test listing blobs."""
        # Mock container client
        mock_container = MagicMock()
        mock_blob1 = MagicMock()
        mock_blob1.name = 'user-123/file1.txt'
        mock_blob1.size = 1024
        mock_blob1.creation_time = datetime.now(timezone.utc)
        mock_blob1.last_modified = datetime.now(timezone.utc)
        mock_blob1.content_settings = MagicMock(content_type='text/plain')
        
        mock_blob2 = MagicMock()
        mock_blob2.name = 'user-123/file2.pdf'
        mock_blob2.size = 2048
        mock_blob2.creation_time = datetime.now(timezone.utc)
        mock_blob2.last_modified = datetime.now(timezone.utc)
        mock_blob2.content_settings = MagicMock(content_type='application/pdf')
        
        mock_container.list_blobs.return_value = [mock_blob1, mock_blob2]
        mock_blob_client.return_value.get_container_client.return_value = mock_container
        
        with self.settings(AZURE_STORAGE_ACCOUNT_NAME='testaccount'):
            service = AzureBlobStorageService()
            blobs = service.list_blobs(user_id='user-123')
            
            self.assertEqual(len(blobs), 2)
            self.assertEqual(blobs[0]['name'], 'user-123/file1.txt')
            self.assertEqual(blobs[1]['name'], 'user-123/file2.pdf')
    
    @patch('fileupload.azure_storage.BlobServiceClient')
    @patch('fileupload.azure_storage.DefaultAzureCredential')
    def test_list_blobs_filters_by_user(self, mock_credential, mock_blob_client):
        """Test that list_blobs filters by user_id."""
        mock_container = MagicMock()
        mock_blob1 = MagicMock()
        mock_blob1.name = 'user-123/file1.txt'
        
        mock_blob2 = MagicMock()
        mock_blob2.name = 'user-456/file2.txt'
        
        mock_container.list_blobs.return_value = [mock_blob1, mock_blob2]
        mock_blob_client.return_value.get_container_client.return_value = mock_container
        
        with self.settings(AZURE_STORAGE_ACCOUNT_NAME='testaccount'):
            service = AzureBlobStorageService()
            blobs = service.list_blobs(user_id='user-123')
            
            # Should only return blobs for user-123
            self.assertEqual(len(blobs), 1)
            self.assertEqual(blobs[0]['name'], 'user-123/file1.txt')


class FileUploadViewTests(TestCase):
    """Test cases for file upload view."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
        self.factory = RequestFactory()
    
    def test_upload_without_authentication(self):
        """Test that upload without auth returns 401."""
        response = self.client.post('/api/upload/')
        self.assertEqual(response.status_code, 401)
    
    @patch('fileupload.views.AzureBlobStorageService')
    def test_upload_without_file(self, mock_storage):
        """Test that upload without file returns 400."""
        request = self.factory.post('/api/upload/')
        request.token_validated = True
        request.user_info = {'user_id': 'test-user'}
        
        view = FileUploadView()
        response = view.post(request)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)
    
    @patch('fileupload.views.AzureBlobStorageService')
    def test_upload_file_too_large(self, mock_storage):
        """Test that large files are rejected."""
        # Create mock file that's too large
        from django.core.files.uploadedfile import SimpleUploadedFile
        mock_file = SimpleUploadedFile("test.txt", b"x" * (51 * 1024 * 1024), content_type="text/plain")
        
        request = self.factory.post('/api/upload/', {'file': mock_file})
        request.token_validated = True
        request.user_info = {'user_id': 'test-user'}
        request.FILES['file'] = mock_file
        
        view = FileUploadView()
        response = view.post(request)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('File too large', response.data['error'])
    
    @patch('fileupload.views.AzureBlobStorageService')
    def test_upload_success(self, mock_storage_class):
        """Test successful file upload."""
        # Mock storage service
        mock_storage = MagicMock()
        mock_storage.upload_file.return_value = {
            'success': True,
            'blob_name': 'test.txt',
            'blob_url': 'https://storage.blob.core.windows.net/uploads/test.txt',
            'size': 1024
        }
        mock_storage_class.return_value = mock_storage
        
        from django.core.files.uploadedfile import SimpleUploadedFile
        mock_file = SimpleUploadedFile("test.txt", b"test content", content_type="text/plain")
        
        request = self.factory.post('/api/upload/', {'file': mock_file})
        request.token_validated = True
        request.user_info = {'user_id': 'test-user'}
        request.FILES['file'] = mock_file
        
        view = FileUploadView()
        response = view.post(request)
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('message', response.data)
        self.assertIn('data', response.data)
    
    @patch('fileupload.views.AzureBlobStorageService')
    def test_upload_configuration_error(self, mock_storage_class):
        """Test upload with configuration error."""
        mock_storage_class.side_effect = ValueError('Config error')
        
        from django.core.files.uploadedfile import SimpleUploadedFile
        mock_file = SimpleUploadedFile("test.txt", b"test content", content_type="text/plain")
        
        request = self.factory.post('/api/upload/', {'file': mock_file})
        request.token_validated = True
        request.user_info = {'user_id': 'test-user'}
        request.FILES['file'] = mock_file
        
        view = FileUploadView()
        response = view.post(request)
        
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data['error'], 'Configuration error')


class FileListViewTests(TestCase):
    """Test cases for file list view."""
    
    def setUp(self):
        """Set up test client."""
        self.factory = RequestFactory()
    
    def test_list_without_authentication(self):
        """Test that list without auth returns 401."""
        request = self.factory.get('/api/files/')
        
        view = FileListView()
        response = view.get(request)
        
        self.assertEqual(response.status_code, 401)
    
    @patch('fileupload.views.AzureBlobStorageService')
    def test_list_files_success(self, mock_storage_class):
        """Test successful file listing."""
        mock_storage = MagicMock()
        mock_storage.list_blobs.return_value = [
            {'name': 'file1.txt', 'size': 1024},
            {'name': 'file2.pdf', 'size': 2048}
        ]
        mock_storage_class.return_value = mock_storage
        
        request = self.factory.get('/api/files/')
        request.token_validated = True
        request.user_info = {'user_id': 'test-user'}
        
        view = FileListView()
        response = view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['data']), 2)
    
    @patch('fileupload.views.AzureBlobStorageService')
    def test_list_files_empty(self, mock_storage_class):
        """Test listing when no files exist."""
        mock_storage = MagicMock()
        mock_storage.list_blobs.return_value = []
        mock_storage_class.return_value = mock_storage
        
        request = self.factory.get('/api/files/')
        request.token_validated = True
        request.user_info = {'user_id': 'test-user'}
        
        view = FileListView()
        response = view.get(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)


class HealthCheckViewTests(TestCase):
    """Test cases for health check view."""
    
    def test_health_check(self):
        """Test health check endpoint."""
        client = Client()
        response = client.get('/api/health/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('message', data)
