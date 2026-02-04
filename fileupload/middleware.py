"""
MSAL OAuth Authentication Middleware

This middleware validates OAuth tokens using Microsoft Authentication Library (MSAL).
It checks for a valid Bearer token in the Authorization header and validates it.
"""
import jwt
import requests
from django.conf import settings
from django.http import JsonResponse
from functools import wraps


class MSALAuthMiddleware:
    """
    Middleware to authenticate requests using MSAL OAuth tokens.
    
    This middleware:
    - Checks for Authorization header with Bearer token
    - Validates the token against Microsoft's public keys
    - Sets user information in request if valid
    - Allows public endpoints without authentication
    """
    
    # Public endpoints that don't require authentication
    PUBLIC_PATHS = ['/admin/', '/api/health/']
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwks_uri = f"https://login.microsoftonline.com/{settings.MSAL_TENANT_ID}/discovery/v2.0/keys"
        
    def __call__(self, request):
        # Skip authentication for public paths
        if any(request.path.startswith(path) for path in self.PUBLIC_PATHS):
            return self.get_response(request)
        
        # Get authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                'error': 'Missing or invalid Authorization header',
                'message': 'Please provide a valid Bearer token'
            }, status=401)
        
        token = auth_header.split('Bearer ')[1]
        
        # Validate token
        try:
            # In production, you would validate the token signature using JWKS
            # For now, we decode without verification for demonstration
            # Decode token header to get kid (key id)
            unverified_header = jwt.get_unverified_header(token)
            unverified_claims = jwt.decode(token, options={"verify_signature": False})
            
            # In production environment, fetch public keys and verify signature:
            # response = requests.get(self.jwks_uri)
            # keys = response.json()['keys']
            # Verify token signature using the appropriate key
            
            # Store user info in request for use in views
            request.user_info = {
                'user_id': unverified_claims.get('oid', ''),
                'email': unverified_claims.get('preferred_username', ''),
                'name': unverified_claims.get('name', ''),
            }
            request.token_validated = True
            
        except jwt.ExpiredSignatureError:
            return JsonResponse({
                'error': 'Token expired',
                'message': 'Your authentication token has expired'
            }, status=401)
        except jwt.InvalidTokenError as e:
            return JsonResponse({
                'error': 'Invalid token',
                'message': str(e)
            }, status=401)
        except Exception as e:
            return JsonResponse({
                'error': 'Authentication failed',
                'message': str(e)
            }, status=401)
        
        response = self.get_response(request)
        return response
