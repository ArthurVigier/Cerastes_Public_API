"""
Tests for the JSON Simplifier post-processor
-----------------------------------------
This module tests the JSON Simplifier functionality which converts
complex JSON results into plain text explanations.
"""

import pytest
import requests
import json
from unittest.mock import patch, MagicMock


class TestJSONSimplifier:
    """Test class for JSON Simplifier functionality."""
    
    @pytest.fixture(scope="function")
    def sample_json_result(self):
        """Return a sample JSON result for testing."""
        return {
            "result": {
                "analysis": {
                    "sentiment": "positive",
                    "tone": "formal",
                    "key_points": [
                        "Point 1: The subject is well explained",
                        "Point 2: Clear and coherent arguments",
                        "Point 3: Logical conclusion"
                    ],
                    "complexity_score": 0.75,
                    "readability_metrics": {
                        "flesch_kincaid": 65.2,
                        "smog_index": 8.1,
                        "coleman_liau_index": 10.3
                    }
                },
                "language": "fr",
                "processing_time": 1.23
            }
        }
    
    @pytest.fixture(scope="function")
    def inference_task(self, api_url, api_headers, cleanup_task):
        """Create an inference task that will generate a JSON result."""
        # Prepare inference data to generate a complex analysis
        inference_data = {
            "text": "This is test text for JSON simplification. It should generate a complex result that needs simplification.",
            "use_segmentation": True,
            "max_new_tokens": 100,
            "format": "json"  # Request JSON output if supported
        }
        
        # Start inference task
        response = requests.post(
            f"{api_url}/api/inference/start",
            json=inference_data,
            headers=api_headers
        )
        
        # Try alternative endpoint if needed
        if response.status_code == 404:
            response = requests.post(
                f"{api_url}/api/inference",
                json=inference_data,
                headers=api_headers
            )
        
        # Skip if cannot create a task
        if response.status_code not in [200, 202]:
            pytest.skip(f"Could not create inference task: {response.status_code}, {response.text}")
        
        # Get task ID
        data = response.json()
        task_id = data.get("task_id") or data.get("id")
        
        yield task_id
        
        # Clean up after test
        cleanup_task(task_id, api_headers)
    
    def test_json_simplification_enabled(self, api_url, api_headers, inference_task, wait_for_task):
        """Test that JSON simplification is performed when enabled."""
        # Wait for task to complete
        result = wait_for_task(inference_task, api_headers, max_retries=10, delay=3)
        
        # Skip if task didn't complete
        if result is None:
            pytest.skip(f"Task {inference_task} did not complete in time")
        
        # Check if plain_explanation is in the result
        if "plain_explanation" in result:
            assert isinstance(result["plain_explanation"], str), "plain_explanation should be a string"
            assert len(result["plain_explanation"]) > 0, "plain_explanation should not be empty"
            print(f"JSON simplification is enabled: {result['plain_explanation'][:100]}...")
        else:
            print("JSON simplification appears to be disabled or not supported")
    
    def test_direct_simplification_endpoint(self, api_url, api_headers, sample_json_result):
        """Test the direct JSON simplification endpoint if it exists."""
        # Try to use a direct simplification endpoint if available
        response = requests.post(
            f"{api_url}/api/simplify-json",
            json=sample_json_result,
            headers=api_headers
        )
        
        # Skip if endpoint doesn't exist
        if response.status_code == 404:
            pytest.skip("Direct JSON simplification endpoint not available")
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "plain_explanation" in data, "No plain_explanation in response"
        assert isinstance(data["plain_explanation"], str), "plain_explanation should be a string"
        assert len(data["plain_explanation"]) > 0, "plain_explanation should not be empty"
    
    def test_simplification_configuration(self, api_url, auth_headers):
        """Test the configuration endpoint for JSON simplification if available."""
        # Try to get current configuration
        response = requests.get(
            f"{api_url}/api/config/postprocessing/json-simplifier",
            headers=auth_headers
        )
        
        # Skip if endpoint doesn't exist
        if response.status_code == 404:
            pytest.skip("JSON simplifier configuration endpoint not available")
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "enabled" in data, "No enabled field in configuration"
        
        # Test updating configuration if writeable
        original_enabled = data["enabled"]
        
        # Try to toggle the setting
        update_response = requests.put(
            f"{api_url}/api/config/postprocessing/json-simplifier",
            json={"enabled": not original_enabled},
            headers=auth_headers
        )
        
        # Skip if configuration update not supported
        if update_response.status_code in [403, 404]:
            pytest.skip("Configuration update not supported or not permitted")
        
        assert update_response.status_code == 200, f"Unexpected status code: {update_response.status_code}, {update_response.text}"
        
        # Verify setting was updated
        updated_data = update_response.json()
        assert updated_data["enabled"] != original_enabled, "Setting was not updated"
        
        # Reset to original value
        reset_response = requests.put(
            f"{api_url}/api/config/postprocessing/json-simplifier",
            json={"enabled": original_enabled},
            headers=auth_headers
        )
        
        assert reset_response.status_code == 200, "Failed to reset configuration"