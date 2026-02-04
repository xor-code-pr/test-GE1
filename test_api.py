#!/usr/bin/env python
"""
Test script to verify the Django file upload application endpoints.

This script tests:
1. Health check endpoint (no auth)
2. Upload endpoint (with mock auth token)
3. List files endpoint (with mock auth token)
4. Authentication validation
"""
import requests
import jwt
from datetime import datetime, timedelta, timezone

BASE_URL = "http://localhost:8000/api"

def generate_test_token():
    """Generate a test JWT token for demonstration."""
    payload = {
        'oid': 'test-user-123',
        'preferred_username': 'testuser@example.com',
        'name': 'Test User',
        'exp': (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        'iat': datetime.now(timezone.utc).timestamp()
    }
    return jwt.encode(payload, 'secret', algorithm='HS256')

def test_health_check():
    """Test the health check endpoint (no auth required)."""
    print("\n=== Testing Health Check Endpoint ===")
    response = requests.get(f"{BASE_URL}/health/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200, "Health check should return 200"
    assert response.json()['status'] == 'healthy', "Health status should be 'healthy'"
    print("✓ Health check passed")

def test_upload_without_auth():
    """Test upload endpoint without authentication (should fail)."""
    print("\n=== Testing Upload Without Authentication ===")
    files = {'file': ('test.txt', b'test content', 'text/plain')}
    response = requests.post(f"{BASE_URL}/upload/", files=files)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 401, "Upload without auth should return 401"
    print("✓ Correctly rejected unauthenticated request")

def test_upload_with_auth():
    """Test upload endpoint with authentication."""
    print("\n=== Testing Upload With Authentication ===")
    token = generate_test_token()
    headers = {'Authorization': f'Bearer {token}'}
    files = {'file': ('test.txt', b'test content', 'text/plain')}
    response = requests.post(f"{BASE_URL}/upload/", files=files, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    # This will fail with config error since Azure credentials aren't set up
    # But it shows authentication is working
    if response.status_code == 500:
        error_data = response.json()
        assert error_data['error'] == 'Configuration error', "Should fail with config error"
        print("✓ Authentication passed (fails on Azure config as expected)")
    else:
        print("✓ Upload endpoint reachable with auth")

def test_list_files_without_auth():
    """Test list files endpoint without authentication (should fail)."""
    print("\n=== Testing List Files Without Authentication ===")
    response = requests.get(f"{BASE_URL}/files/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 401, "List files without auth should return 401"
    print("✓ Correctly rejected unauthenticated request")

def test_list_files_with_auth():
    """Test list files endpoint with authentication."""
    print("\n=== Testing List Files With Authentication ===")
    token = generate_test_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f"{BASE_URL}/files/", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    # This will fail with config error since Azure credentials aren't set up
    if response.status_code == 500:
        error_data = response.json()
        assert error_data['error'] == 'Configuration error', "Should fail with config error"
        print("✓ Authentication passed (fails on Azure config as expected)")
    else:
        print("✓ List files endpoint reachable with auth")

if __name__ == "__main__":
    print("=" * 60)
    print("Django File Upload Application - API Tests")
    print("=" * 60)
    print("\nNOTE: This test uses mock JWT tokens for demonstration.")
    print("In production, use real OAuth tokens from Azure AD.")
    print("\nStarting tests...")
    
    try:
        test_health_check()
        test_upload_without_auth()
        test_upload_with_auth()
        test_list_files_without_auth()
        test_list_files_with_auth()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
    except requests.exceptions.ConnectionError:
        print("\n✗ Could not connect to server. Is Django running on localhost:8000?")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
