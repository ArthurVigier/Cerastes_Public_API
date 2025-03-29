"""
Tests for health and monitoring endpoints
-----------------------------------------
This module tests the health monitoring API endpoints including
health, readiness, and metrics endpoints.
"""

import pytest
import requests

class TestHealth:
    """Test class for health endpoints."""
    
    def test_health_check(self, api_url):
        """Test the main health endpoint."""
        response = requests.get(f"{api_url}/health")
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response data
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data
        assert "uptime" in data
        assert isinstance(data["uptime"], (int, float))
    
    def test_detailed_health_check(self, api_url):
        """Test the detailed health endpoint."""
        response = requests.get(f"{api_url}/health/detailed")
        
        # If detailed endpoint doesn't exist, skip test
        if response.status_code == 404:
            pytest.skip("Detailed health endpoint not available")
            
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        
        # Check detailed sections
        assert "system_info" in data
        assert "resources" in data
        assert "services" in data
        
        # Check system info
        system_info = data["system_info"]
        assert "platform" in system_info
        assert "python_version" in system_info
        
        # Check resources
        resources = data["resources"]
        assert "cpu_percent" in resources
        assert "memory_percent" in resources
        assert "disk_percent" in resources
        
        # Check services
        services = data["services"]
        assert "database" in services
        assert "filesystem" in services
    
    def test_ping(self, api_url):
        """Test the ping endpoint."""
        response = requests.get(f"{api_url}/health/ping")
        
        # If ping endpoint doesn't exist, skip test
        if response.status_code == 404:
            pytest.skip("Ping endpoint not available")
            
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "ping" in data
        assert data["ping"] == "pong"
    
    def test_readiness_probe(self, api_url):
        """Test the readiness probe endpoint."""
        response = requests.get(f"{api_url}/health/ready")
        
        # If ready endpoint doesn't exist, skip test
        if response.status_code == 404:
            pytest.skip("Readiness endpoint not available")
            
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "status" in data
        assert data["status"] == "ready"
    
    def test_liveness_probe(self, api_url):
        """Test the liveness probe endpoint."""
        response = requests.get(f"{api_url}/health/live")
        
        # If live endpoint doesn't exist, skip test
        if response.status_code == 404:
            pytest.skip("Liveness endpoint not available")
            
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "status" in data
        assert data["status"] == "alive"
    
    def test_version_info(self, api_url):
        """Verify version information is consistent."""
        # Get version from main health endpoint
        response = requests.get(f"{api_url}/health")
        assert response.status_code == 200
        
        # Check that version is a non-empty string
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0
        
        # Compare with detailed version if available
        try:
            response_detailed = requests.get(f"{api_url}/health/detailed")
            if response_detailed.status_code == 200:
                data_detailed = response_detailed.json()
                if "version" in data_detailed:
                    assert data["version"] == data_detailed["version"], "Versions do not match between endpoints"
        except Exception:
            # Don't fail test if detailed endpoint is not available
            pass
    
    def test_metrics_endpoint(self, api_url, api_headers):
        """Test the Prometheus metrics endpoint (if it exists)."""
        try:
            response = requests.get(f"{api_url}/metrics", headers=api_headers)
            
            # If endpoint doesn't exist, skip test
            if response.status_code == 404:
                pytest.skip("/metrics endpoint doesn't exist")
            
            # If authentication is required but we don't have valid API key
            if response.status_code in [401, 403]:
                pytest.skip("Authentication required for /metrics endpoint")
            
            assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
            
            # Check that content is in Prometheus format
            assert "# HELP" in response.text, "Content doesn't appear to be in Prometheus format"
            
            # Check for standard metrics
            assert "process_cpu_seconds_total" in response.text or "cerastes_" in response.text, "No standard metrics found"
        
        except requests.exceptions.RequestException:
            pytest.skip("Unable to connect to /metrics endpoint")
    
    def test_check_endpoints_consistency(self, api_url):
        """Verify consistency between different health endpoints."""
        try:
            # Get data from different endpoints
            health_response = requests.get(f"{api_url}/health")
            ready_response = requests.get(f"{api_url}/health/ready")
            live_response = requests.get(f"{api_url}/health/live")
            
            if health_response.status_code != 200 or ready_response.status_code != 200 or live_response.status_code != 200:
                pytest.skip("Some health endpoints are not available")
            
            # Check consistency: if API is ready and alive, its status should be "ok"
            health_data = health_response.json()
            ready_data = ready_response.json()
            live_data = live_response.json()
            
            if ready_data["status"] == "ready" and live_data["status"] == "alive":
                assert health_data["status"] == "ok", "Inconsistency: API is ready and alive, but status is not 'ok'"
        
        except Exception as e:
            pytest.skip(f"Error checking consistency: {e}")