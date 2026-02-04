#!/usr/bin/env python
"""Generate a test JWT token for UI testing."""
import jwt
from datetime import datetime, timedelta, timezone

payload = {
    'oid': 'test-user-123',
    'preferred_username': 'testuser@example.com',
    'name': 'Test User',
    'exp': (datetime.now(timezone.utc) + timedelta(hours=24)).timestamp(),
    'iat': datetime.now(timezone.utc).timestamp()
}

token = jwt.encode(payload, 'secret', algorithm='HS256')
print("\n" + "="*80)
print("TEST JWT TOKEN FOR UI")
print("="*80)
print("\nToken (copy this to the UI):")
print(token)
print("\n" + "="*80)
print("\nNOTE: This is a demo token for testing only.")
print("In production, use real OAuth tokens from Azure AD.")
print("="*80 + "\n")
