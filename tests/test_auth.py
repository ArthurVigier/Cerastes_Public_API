"""
Tests for authentication functionality
-------------------------------------
This module tests the authentication API including user registration, 
login, token generation, and API key management.
"""

import pytest
import requests
import uuid
from typing import Dict, Any

class TestAuth:
    """Test class for authentication endpoints."""
    
    @pytest.fixture(scope="function")
    def unique_user_data(self):
        """Create unique registration data for each test."""
        username = f"testuser_{uuid.uuid4().hex[:8]}"
        return {
            "username": username,
            "email": f"{username}@example.com",
            "password": "Password123!",
            "full_name": f"Test User {username}"
        }
    
    @pytest.fixture(scope="function")
    def register_single_user(self, api_url, unique_user_data):
        """Register a single user for an individual test."""
        response = requests.post(f"{api_url}/auth/register", json=unique_user_data)
        
        if response.status_code == 403 and "registration is disabled" in response.text.lower():
            pytest.skip("User registration is disabled on this server")
        
        if response.status_code != 201:
            pytest.skip(f"Failed to register test user: {response.status_code}, {response.text}")
        
        return response.json()
    
    @pytest.fixture(scope="function")
    def login_user(self, api_url, unique_user_data, register_single_user):
        """Login a user and get their token."""
        login_data = {
            "username": unique_user_data["username"],
            "password": unique_user_data["password"]
        }
        
        response = requests.post(f"{api_url}/auth/token", data=login_data)
        
        if response.status_code != 200:
            pytest.skip(f"Failed to log in user: {response.status_code}, {response.text}")
        
        return response.json()
    
    @pytest.fixture(scope="function")
    def user_api_key(self, api_url, login_user):
        """Create an API key for a test user."""
        headers = {"Authorization": f"Bearer {login_user['access_token']}"}
        key_data = {"name": f"Test Key {uuid.uuid4().hex[:8]}"}
        
        response = requests.post(f"{api_url}/auth/api-keys", json=key_data, headers=headers)
        
        if response.status_code != 201:
            pytest.skip(f"Failed to create API key: {response.status_code}, {response.text}")
        
        return response.json()
    
    def test_health_check(self, api_url):
        """Verify that the API health endpoint is working."""
        response = requests.get(f"{api_url}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
    
    def test_register_user(self, api_url, unique_user_data):
        """Test user registration."""
        response = requests.post(f"{api_url}/auth/register", json=unique_user_data)
        
        if response.status_code == 403 and "registration is disabled" in response.text.lower():
            pytest.skip("User registration is disabled on this server")
        
        assert response.status_code == 201, f"Unexpected status code: {response.status_code}, {response.text}"
        
        data = response.json()
        assert data["username"] == unique_user_data["username"]
        assert data["email"] == unique_user_data["email"]
        assert "id" in data
    
    def test_login(self, api_url, register_single_user, unique_user_data):
        """Test user login."""
        login_data = {
            "username": unique_user_data["username"],
            "password": unique_user_data["password"]
        }
        
        response = requests.post(f"{api_url}/auth/token", data=login_data)
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_at" in data
    
    def test_get_user_info(self, api_url, login_user):
        """Test retrieving user information."""
        headers = {"Authorization": f"Bearer {login_user['access_token']}"}
        
        response = requests.get(f"{api_url}/auth/me", headers=headers)
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        data = response.json()
        assert "username" in data
        assert "email" in data
        assert "id" in data
    
    def test_create_api_key(self, api_url, login_user):
        """Test API key creation."""
        headers = {"Authorization": f"Bearer {login_user['access_token']}"}
        key_data = {"name": "Test API Key"}
        
        response = requests.post(f"{api_url}/auth/api-keys", json=key_data, headers=headers)
        assert response.status_code == 201, f"Unexpected status code: {response.status_code}, {response.text}"
        
        data = response.json()
        assert "key" in data
        assert data["name"] == "Test API Key"
        assert "id" in data
    
    def test_list_api_keys(self, api_url, login_user, user_api_key):
        """Test listing user's API keys."""
        headers = {"Authorization": f"Bearer {login_user['access_token']}"}
        
        response = requests.get(f"{api_url}/auth/api-keys", headers=headers)
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        key_found = False
        for key in data:
            if key["id"] == user_api_key["id"]:
                key_found = True
                break
        
        assert key_found, "Created API key not found in the list"
    
    def test_deactivate_api_key(self, api_url, login_user, user_api_key):
        """Test API key deactivation."""
        headers = {"Authorization": f"Bearer {login_user['access_token']}"}
        
        response = requests.put(
            f"{api_url}/auth/api-keys/{user_api_key['id']}/deactivate",
            headers=headers
        )
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        data = response.json()
        assert not data["is_active"], "API key was not deactivated"
    
    def test_activate_api_key(self, api_url, login_user, user_api_key):
        """Test API key activation."""
        headers = {"Authorization": f"Bearer {login_user['access_token']}"}
        
        # First deactivate the key
        requests.put(
            f"{api_url}/auth/api-keys/{user_api_key['id']}/deactivate",
            headers=headers
        )
        
        # Then activate it
        response = requests.put(
            f"{api_url}/auth/api-keys/{user_api_key['id']}/activate",
            headers=headers
        )
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        data = response.json()
        assert data["is_active"], "API key was not activated"
    
    def test_access_without_token(self, api_url):
        """Test access to a protected route without token."""
        response = requests.get(f"{api_url}/auth/me")
        assert response.status_code in [401, 403], f"Unexpected status code: {response.status_code}"
    
    def test_delete_api_key(self, api_url, login_user, user_api_key):
        """Test API key deletion."""
        headers = {"Authorization": f"Bearer {login_user['access_token']}"}
        
        response = requests.delete(
            f"{api_url}/auth/api-keys/{user_api_key['id']}",
            headers=headers
        )
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Verify that the key has been deleted
        response = requests.get(f"{api_url}/auth/api-keys", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        key_exists = False
        for key in data:
            if key.get("id") == user_api_key["id"]:
                key_exists = True
                break
        
        assert not key_exists, "API key was not deleted"