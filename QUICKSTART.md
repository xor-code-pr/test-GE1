# Quick Start Guide

## Overview
This Django application enables users to upload documents to Azure Blob Storage with MSAL OAuth authentication.

## Features
- ✅ MSAL OAuth authentication for API security
- ✅ Azure Blob Storage integration with managed identity
- ✅ File upload with automatic organization by user
- ✅ File listing per authenticated user
- ✅ Health check endpoint
- ✅ RESTful API design

## Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

Edit `.env`:
```env
SECRET_KEY=<generate-with-django>
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

AZURE_STORAGE_ACCOUNT_NAME=<your-storage-account>
AZURE_STORAGE_CONTAINER_NAME=uploads

MSAL_CLIENT_ID=<your-azure-app-id>
MSAL_TENANT_ID=<your-tenant-id>
```

Generate SECRET_KEY:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. Initialize Database
```bash
python manage.py migrate
```

### 4. Run Development Server
```bash
python manage.py runserver
```

## API Endpoints

### Health Check (No Auth)
```bash
curl http://localhost:8000/api/health/
```

### Upload File (Requires Auth)
```bash
curl -X POST \
  -H "Authorization: Bearer <your-oauth-token>" \
  -F "file=@path/to/file.pdf" \
  http://localhost:8000/api/upload/
```

### List Files (Requires Auth)
```bash
curl -H "Authorization: Bearer <your-oauth-token>" \
  http://localhost:8000/api/files/
```

## Testing

Run the included test script:
```bash
python test_api.py
```

Note: This tests authentication flow with mock tokens. In production, use real OAuth tokens from Azure AD.

## Azure Setup Required

1. **Storage Account**: Create Azure Storage Account
2. **Container**: Create a blob container (default: "uploads")
3. **Managed Identity**: 
   - For local dev: Use Azure CLI (`az login`)
   - For production: Enable managed identity on Azure App Service
4. **RBAC**: Grant "Storage Blob Data Contributor" role to the identity
5. **Azure AD App**: Register application for MSAL OAuth
   - Configure API permissions
   - Generate client secret (for web apps)

## Security Notes

⚠️ **IMPORTANT**: The current JWT implementation does not verify token signatures. This is intentional for demonstration purposes.

For production deployment:
1. Uncomment the production JWT verification code in `fileupload/middleware.py`
2. Implement proper JWKS validation
3. Set `DEBUG=False` in production
4. Use proper `SECRET_KEY`
5. Configure `ALLOWED_HOSTS`
6. Use HTTPS only
7. Enable Django security middleware

See README.md for complete documentation.

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ OAuth Token
       ▼
┌─────────────────┐
│ MSAL Middleware │ ◄── Validates JWT
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Django Views   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Azure Storage   │ ◄── Managed Identity
│    Service      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Azure Blob     │
│   Storage       │
└─────────────────┘
```

## File Organization

Uploaded files are organized by user:
```
container/
  ├── user-id-1/
  │   ├── 20260204_120000_uuid1.pdf
  │   └── 20260204_130000_uuid2.jpg
  └── user-id-2/
      └── 20260204_140000_uuid3.docx
```

## Support

For issues or questions, refer to:
- README.md (complete documentation)
- Django documentation: https://docs.djangoproject.com/
- Azure Storage SDK: https://learn.microsoft.com/azure/storage/
- MSAL documentation: https://learn.microsoft.com/azure/active-directory/develop/
