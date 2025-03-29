"""
Main pytest configuration for API testing with fixtures for authentication, database, and API clients.
"""

import pytest
import os
import requests
import time
import uuid
import json
from pathlib import Path
from typing import Dict, Any, Generator

# URL of the API
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Test API Key (can be overridden by environment variable)
TEST_API_KEY = os.environ.get("TEST_API_KEY", "test-api-key-for-automation")

# Placeholder for database session if needed
try:
    from db import engine, SessionLocal, get_db
    from db.models import User, ApiKey
    HAS_DB_ACCESS = True
except ImportError:
    HAS_DB_ACCESS = False
    print("Warning: Database models could not be imported. DB tests will be skipped.")

# =====================
# UTILITY FUNCTIONS
# =====================

def generate_unique_username():
    """Generate a unique username for test user registration."""
    return f"testuser_{uuid.uuid4().hex[:8]}"

def get_api_key_headers(api_key):
    """Create headers with API key authentication."""
    return {"X-API-Key": api_key}

def get_token_headers(token):
    """Create headers with JWT token authentication."""
    return {"Authorization": f"Bearer {token}"}

# =====================
# BASIC FIXTURES
# =====================

@pytest.fixture(scope="session")
def api_url():
    """Return the base API URL."""
    return BASE_URL

@pytest.fixture(scope="session")
def health_check(api_url):
    """Check if the API is running before tests."""
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code != 200:
            pytest.skip(f"API is not available. Status code: {response.status_code}")
    except requests.RequestException as e:
        pytest.skip(f"API is not reachable: {str(e)}")
    return True

# =====================
# USER & AUTH FIXTURES
# =====================

@pytest.fixture(scope="session")
def test_user_credentials():
    """Return credentials for test user registration."""
    username = generate_unique_username()
    return {
        "username": username,
        "email": f"{username}@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User"
    }

@pytest.fixture(scope="session")
def registered_user(api_url, test_user_credentials, health_check):
    """Register a test user and return user data."""
    # Try to register new user
    response = requests.post(
        f"{api_url}/auth/register", 
        json=test_user_credentials
    )
    
    # If registration is disabled or fails, skip dependent tests
    if response.status_code == 403 and "registration is disabled" in response.text.lower():
        pytest.skip("User registration is disabled on this server")
    
    if response.status_code != 201:
        pytest.skip(f"Failed to register test user: {response.status_code}, {response.text}")
    
    return response.json()

@pytest.fixture(scope="session")
def auth_token(api_url, test_user_credentials, registered_user, health_check):
    """Get auth token for the test user."""
    # Prepare login data
    login_data = {
        "username": test_user_credentials["username"],
        "password": test_user_credentials["password"]
    }
    
    # Login to get token
    response = requests.post(
        f"{api_url}/auth/token",
        data=login_data  # Note: uses form data, not JSON
    )
    
    if response.status_code != 200:
        pytest.skip(f"Failed to get auth token: {response.status_code}, {response.text}")
    
    token_data = response.json()
    return token_data["access_token"]

@pytest.fixture(scope="session")
def api_key(api_url, auth_token, health_check):
    """Create and return an API key for the test user."""
    # If TEST_API_KEY environment variable is set, use it
    if os.environ.get("TEST_API_KEY"):
        return os.environ.get("TEST_API_KEY")
    
    # Otherwise create a new API key
    headers = get_token_headers(auth_token)
    key_data = {"name": "Test API Key"}
    
    response = requests.post(
        f"{api_url}/auth/api-keys",
        json=key_data,
        headers=headers
    )
    
    if response.status_code != 201:
        pytest.skip(f"Failed to create API key: {response.status_code}, {response.text}")
    
    return response.json()["key"]

@pytest.fixture(scope="function")
def auth_headers(auth_token):
    """Return headers with JWT token authentication."""
    return get_token_headers(auth_token)

@pytest.fixture(scope="function")
def api_headers(api_key):
    """Return headers with API key authentication."""
    return get_api_key_headers(api_key)

# =====================
# DATABASE FIXTURES
# =====================

@pytest.fixture(scope="function")
def db_session():
    """Provide a database session if database access is available."""
    if not HAS_DB_ACCESS:
        pytest.skip("Database access not available")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =====================
# TEST DATA FIXTURES
# =====================

@pytest.fixture(scope="function")
def sample_text():
    """Sample text for inference tests."""
    return """
    The quick brown fox jumps over the lazy dog. This pangram contains every
    letter of the English alphabet at least once. Pangrams are often used to 
    test fonts, keyboards, and OCR systems.
    """

@pytest.fixture(scope="function")
def sample_video_path():
    """Return path to sample video if available."""
    video_path = os.environ.get("SAMPLE_VIDEO_PATH")
    if not video_path or not os.path.exists(video_path):
        pytest.skip("Sample video not available. Set SAMPLE_VIDEO_PATH environment variable.")
    return video_path

@pytest.fixture(scope="function")
def sample_audio_path():
    """Return path to sample audio if available."""
    audio_path = os.environ.get("SAMPLE_AUDIO_PATH")
    if not audio_path or not os.path.exists(audio_path):
        pytest.skip("Sample audio not available. Set SAMPLE_AUDIO_PATH environment variable.")
    return audio_path

# =====================
# TASK MANAGEMENT FIXTURES
# =====================

@pytest.fixture(scope="function")
def wait_for_task():
    """Return a function that waits for a task to complete."""
    def _wait_for_task(task_id, headers, endpoint="/api/tasks/{task_id}", max_retries=30, delay=5):
        """
        Wait for a task to complete and return its result.
        
        Args:
            task_id: ID of the task to wait for
            headers: Authentication headers
            endpoint: API endpoint pattern with {task_id} placeholder
            max_retries: Maximum number of retries
            delay: Delay between retries in seconds
            
        Returns:
            Task data dictionary or None if failed
        """
        formatted_endpoint = endpoint.format(task_id=task_id)
        
        for i in range(max_retries):
            response = requests.get(f"{BASE_URL}{formatted_endpoint}", headers=headers)
            if response.status_code != 200:
                print(f"Error retrieving task status: {response.status_code}")
                time.sleep(delay)
                continue
                
            data = response.json()
            
            # If task failed, return None
            if data["status"] == "failed":
                print(f"Task failed: {data.get('error', 'Unknown error')}")
                return None
            
            # If task is completed, return results
            if data["status"] == "completed":
                return data
                
            # Display progress
            print(f"Waiting for task... Progress: {data.get('progress', 0):.0f}% (attempt {i+1}/{max_retries})")
                
            # Wait before retrying
            time.sleep(delay)
        
        print(f"Timeout waiting for task {task_id}")
        return None
    
    return _wait_for_task

# =====================
# CLEANUP FIXTURES
# =====================

@pytest.fixture(scope="function")
def cleanup_task():
    """Return a function to clean up a task after test."""
    def _cleanup_task(task_id, headers):
        """Clean up a task by ID."""
        if not task_id:
            return False
        
        try:
            response = requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=headers)
            return response.status_code == 200
        except Exception as e:
            print(f"Error cleaning up task {task_id}: {e}")
            return False
    
    return _cleanup_task

@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    """Perform cleanup after all tests are done."""
    yield
    # Additional cleanup can be added here
    print("Test suite completed. Cleaning up...")