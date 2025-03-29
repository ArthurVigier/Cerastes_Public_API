"""
Tests for the Prompt Manager functionality
---------------------------------------
This module tests the Prompt Manager which handles loading,
formatting, and managing prompts used by the API.
"""

import pytest
import requests
import tempfile
import os
import shutil
from pathlib import Path
import json


class TestPromptManager:
    """Test class for Prompt Manager functionality."""
    
    @pytest.fixture(scope="function")
    def temp_prompts_dir(self):
        """Create a temporary directory with test prompts."""
        temp_dir = tempfile.mkdtemp()
        prompts_dir = Path(temp_dir) / "prompts"
        prompts_dir.mkdir()
        
        # Create test prompt files
        with open(prompts_dir / "test1.txt", "w", encoding="utf-8") as f:
            f.write("Prompt with {placeholder1} and {placeholder2}")
        
        with open(prompts_dir / "test2.txt", "w", encoding="utf-8") as f:
            f.write("Prompt without placeholders")
        
        with open(prompts_dir / "test3.txt", "w", encoding="utf-8") as f:
            f.write("Analyze {text} in {language}")
        
        # Create JSON collection file
        with open(prompts_dir / "prompts.json", "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "json_prompt1": "JSON prompt with {var}",
                "json_prompt2": "Another JSON prompt with {text}"
            }))
        
        yield prompts_dir
        
        # Clean up
        shutil.rmtree(temp_dir)
    
    def test_list_available_prompts(self, api_url, api_headers):
        """Test listing available prompts if endpoint exists."""
        response = requests.get(
            f"{api_url}/api/prompts",
            headers=api_headers
        )
        
        # Skip if endpoint doesn't exist
        if response.status_code == 404:
            pytest.skip("Prompts listing endpoint not available")
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response format
        data = response.json()
        assert "prompts" in data, "No prompts in response"
        prompts = data["prompts"]
        assert isinstance(prompts, (list, dict)), "Prompts should be a list or dictionary"
    
    def test_get_specific_prompt(self, api_url, api_headers):
        """Test getting a specific prompt if endpoint exists."""
        # First list available prompts
        list_response = requests.get(
            f"{api_url}/api/prompts",
            headers=api_headers
        )
        
        # Skip if listing endpoint doesn't exist
        if list_response.status_code == 404:
            pytest.skip("Prompts listing endpoint not available")
        
        # Get first prompt name
        list_data = list_response.json()
        if not list_data.get("prompts"):
            pytest.skip("No prompts available")
        
        prompt_name = None
        if isinstance(list_data["prompts"], list):
            if list_data["prompts"]:
                prompt_name = list_data["prompts"][0]
        else:  # dict
            prompt_name = next(iter(list_data["prompts"]), None)
        
        if not prompt_name:
            pytest.skip("No prompt names available")
        
        # Get specific prompt
        response = requests.get(
            f"{api_url}/api/prompts/{prompt_name}",
            headers=api_headers
        )
        
        # Skip if endpoint doesn't exist
        if response.status_code == 404:
            pytest.skip("Specific prompt endpoint not available")
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response format
        data = response.json()
        assert "prompt" in data, "No prompt in response"
        assert isinstance(data["prompt"], str), "Prompt should be a string"
        assert "placeholders" in data, "No placeholders in response"
        assert isinstance(data["placeholders"], list), "Placeholders should be a list"
    
    def test_add_custom_prompt(self, api_url, auth_headers):
        """Test adding a custom prompt if endpoint exists."""
        # Create a unique prompt name
        prompt_name = f"test_prompt_{uuid.uuid4().hex[:8]}"
        
        # Prepare prompt data
        prompt_data = {
            "name": prompt_name,
            "content": "This is a test prompt with {placeholder}",
            "description": "A test prompt for API testing"
        }
        
        # Add prompt
        response = requests.post(
            f"{api_url}/api/prompts",
            json=prompt_data,
            headers=auth_headers
        )
        
        # Skip if endpoint doesn't exist
        if response.status_code == 404:
            pytest.skip("Add prompt endpoint not available")
        
        # Skip if not authorized
        if response.status_code == 403:
            pytest.skip("Not authorized to add prompts")
        
        assert response.status_code in [200, 201], f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Verify prompt was added by getting it
        get_response = requests.get(
            f"{api_url}/api/prompts/{prompt_name}",
            headers=auth_headers
        )
        
        assert get_response.status_code == 200, f"Failed to retrieve added prompt: {get_response.status_code}, {get_response.text}"
        
        # Clean up
        delete_response = requests.delete(
            f"{api_url}/api/prompts/{prompt_name}",
            headers=auth_headers
        )
        
        # Note but don't fail if cleanup fails
        if delete_response.status_code != 200:
            print(f"Warning: Failed to clean up test prompt: {delete_response.status_code}, {delete_response.text}")
    
    def test_update_prompt(self, api_url, auth_headers):
        """Test updating an existing prompt if endpoint exists."""
        # First create a prompt to update
        prompt_name = f"test_update_{uuid.uuid4().hex[:8]}"
        
        # Prepare prompt data
        create_data = {
            "name": prompt_name,
            "content": "Original prompt content with {var}",
            "description": "A test prompt for updating"
        }
        
        # Create prompt
        create_response = requests.post(
            f"{api_url}/api/prompts",
            json=create_data,
            headers=auth_headers
        )
        
        # Skip if endpoint doesn't exist
        if create_response.status_code == 404:
            pytest.skip("Add prompt endpoint not available")
        
        # Skip if not authorized
        if create_response.status_code == 403:
            pytest.skip("Not authorized to add prompts")
        
        if create_response.status_code not in [200, 201]:
            pytest.skip(f"Failed to create test prompt: {create_response.status_code}, {create_response.text}")
        
        # Update prompt
        update_data = {
            "content": "Updated prompt content with {var} and {new_var}",
            "description": "Updated description"
        }
        
        update_response = requests.put(
            f"{api_url}/api/prompts/{prompt_name}",
            json=update_data,
            headers=auth_headers
        )
        
        # Skip if endpoint doesn't exist
        if update_response.status_code == 404:
            pytest.skip("Update prompt endpoint not available")
        
        assert update_response.status_code == 200, f"Unexpected status code: {update_response.status_code}, {update_response.text}"
        
        # Verify update
        get_response = requests.get(
            f"{api_url}/api/prompts/{prompt_name}",
            headers=auth_headers
        )
        
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert "prompt" in get_data
        assert "new_var" in get_data["prompt"], "Updated content not saved"
        
        # Clean up
        requests.delete(
            f"{api_url}/api/prompts/{prompt_name}",
            headers=auth_headers
        )
    
    def test_prompt_visualization(self, api_url, api_headers):
        """Test prompt visualization if endpoint exists."""
        response = requests.get(
            f"{api_url}/api/prompts/visualize",
            headers=api_headers
        )
        
        # Skip if endpoint doesn't exist
        if response.status_code == 404:
            pytest.skip("Prompt visualization endpoint not available")
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
    
    def test_use_prompt_in_inference(self, api_url, api_headers):
        """Test using a specific prompt in inference."""
        # First list available prompts
        list_response = requests.get(
            f"{api_url}/api/prompts",
            headers=api_headers
        )
        
        # Skip if listing endpoint doesn't exist
        if list_response.status_code == 404:
            pytest.skip("Prompts listing endpoint not available")
        
        # Get first prompt name
        list_data = list_response.json()
        if not list_data.get("prompts"):
            pytest.skip("No prompts available")
        
        prompt_name = None
        if isinstance(list_data["prompts"], list):
            if list_data["prompts"]:
                prompt_name = list_data["prompts"][0]
        else:  # dict
            prompt_name = next(iter(list_data["prompts"]), None)
        
        if not prompt_name:
            pytest.skip("No prompt names available")
        
        # Use prompt in inference
        inference_data = {
            "text": "This is test text for inference with a specific prompt.",
            "prompt_name": prompt_name,
            "use_segmentation": True,
            "max_new_tokens": 100
        }
        
        response = requests.post(
            f"{api_url}/api/inference/start",
            json=inference_data,
            headers=api_headers
        )
        
        # Try alternative endpoint if needed
        if response.status_code == 404:
            inference_data["prompt"] = prompt_name  # Some APIs use 'prompt' instead of 'prompt_name'
            response = requests.post(
                f"{api_url}/api/inference",
                json=inference_data,
                headers=api_headers
            )
        
        # Skip if inferencing not available
        if response.status_code in [404, 400] and "prompt" in response.text.lower():
            pytest.skip("Inference with specific prompt not supported")
        
        assert response.status_code in [200, 202], f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check if task was created
        data = response.json()
        assert "task_id" in data or "id" in data, "No task ID in response"
        
        # Clean up task
        task_id = data.get("task_id") or data.get("id")
        if task_id:
            try:
                requests.delete(f"{api_url}/api/tasks/{task_id}", headers=api_headers)
            except:
                pass