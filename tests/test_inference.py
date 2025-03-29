"""
Tests for text inference functionality
------------------------------------
This module tests the text inference API endpoints including
task creation, monitoring, and result retrieval.
"""

import pytest
import requests
import time
from typing import Dict, Any

class TestInference:
    """Test class for text inference endpoints."""
    
    @pytest.fixture(scope="function")
    def inference_task(self, api_url, api_headers, sample_text, cleanup_task):
        """Create a text inference task and yield its ID for testing."""
        # Prepare inference data
        inference_data = {
            "text": sample_text,
            "use_segmentation": True,
            "max_new_tokens": 500
        }
        
        # Start inference task
        response = requests.post(
            f"{api_url}/api/inference/start",
            json=inference_data,
            headers=api_headers
        )
        
        # Handle case when the endpoint might have different format
        if response.status_code == 404:
            response = requests.post(
                f"{api_url}/api/inference", 
                json=inference_data,
                headers=api_headers
            )
        
        # Skip test if API not available
        if response.status_code not in [200, 202]:
            pytest.skip(f"Failed to create inference task: {response.status_code}, {response.text}")
        
        # Extract task ID from response
        data = response.json()
        task_id = data.get("task_id") or data.get("id")
        
        # Yield task ID for the test
        yield task_id
        
        # Clean up after test
        cleanup_task(task_id, api_headers)
    
    def test_inference_without_api_key(self, api_url, sample_text):
        """Test inference request without API key."""
        # Prepare inference data
        inference_data = {
            "text": sample_text,
            "use_segmentation": True,
            "max_new_tokens": 500
        }
        
        # Send request without authentication
        response = requests.post(f"{api_url}/api/inference/start", json=inference_data)
        assert response.status_code in [401, 403], f"Expected auth error, got: {response.status_code}"
    
    def test_start_inference(self, api_url, api_headers, sample_text):
        """Test starting an inference task."""
        # Prepare inference data
        inference_data = {
            "text": sample_text,
            "use_segmentation": True,
            "max_new_tokens": 500,
            "timeout_seconds": 120
        }
        
        # Start inference task
        response = requests.post(
            f"{api_url}/api/inference/start",
            json=inference_data,
            headers=api_headers
        )
        
        # Handle case when the endpoint might have different format
        if response.status_code == 404:
            response = requests.post(
                f"{api_url}/api/inference", 
                json=inference_data,
                headers=api_headers
            )
        
        # Check if API is in compatibility mode
        if response.status_code == 400 and "compatibility mode" in response.text.lower():
            pytest.skip("API is in compatibility mode")
        
        assert response.status_code in [200, 202], f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Validate response format
        data = response.json()
        assert "task_id" in data or "id" in data, "Task ID missing in response"
        assert "status" in data, "Status missing in response"
        assert data["status"] in ["pending", "running"], f"Unexpected status: {data['status']}"
    
    def test_get_inference_status(self, api_url, api_headers, inference_task):
        """Test retrieving the status of an inference task."""
        # Get task status
        response = requests.get(
            f"{api_url}/api/tasks/{inference_task}",
            headers=api_headers
        )
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Validate response
        data = response.json()
        assert "status" in data, "Status missing in response"
        assert "progress" in data, "Progress missing in response"
        assert "type" in data, "Type missing in response"
        assert data["type"] == "text_inference", f"Unexpected task type: {data['type']}"
    
    def test_wait_for_inference_completion(self, api_url, api_headers, inference_task, wait_for_task):
        """Test waiting for an inference task to complete."""
        # Wait for task completion with a shorter timeout for testing
        result = wait_for_task(inference_task, api_headers, max_retries=10, delay=3)
        
        # Verify task completed successfully
        assert result is not None, "Task did not complete successfully"
        assert result["status"] == "completed", f"Unexpected status: {result['status']}"
        assert "results" in result, "Results missing in response"
        
        # Validate results format
        assert isinstance(result["results"], dict), "Results should be a dictionary"
        assert len(result["results"]) > 0, "Results should not be empty"
    
    def test_custom_session(self, api_url, api_headers, inference_task):
        """Test running a custom session on an inference task."""
        # Prepare custom session data
        session_data = {
            "system_prompt": "Summarize the following text in a few sentences:\n\n{text}",
            "user_input": "",
            "max_new_tokens": 200
        }
        
        # Start custom session
        response = requests.post(
            f"{api_url}/api/inference/session/{inference_task}/custom_summary",
            json=session_data,
            headers=api_headers
        )
        
        # If endpoint not available or in compatibility mode, skip test
        if response.status_code == 404:
            pytest.skip("Custom session endpoint not available")
            
        if response.status_code == 400 and "compatibility mode" in response.text.lower():
            pytest.skip("API is in compatibility mode")
        
        assert response.status_code in [200, 202], f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Validate response
        data = response.json()
        assert "task_id" in data, "Task ID missing in response"
        assert "parent_task_id" in data, "Parent task ID missing in response"
        assert data["parent_task_id"] == inference_task, "Parent task ID mismatch"
        assert "session_name" in data, "Session name missing in response"
        assert data["session_name"] == "custom_summary", "Session name mismatch"
    
    def test_batch_inference(self, api_url, api_headers, sample_text, cleanup_task):
        """Test batch inference processing."""
        # Prepare batch data
        batch_data = {
            "texts": [
                sample_text,
                "AI safety is a critical concern for researchers and policymakers alike.",
                "The adoption of renewable energy is accelerating globally."
            ],
            "use_segmentation": True,
            "max_new_tokens": 500,
            "max_concurrent": 2
        }
        
        # Start batch inference
        response = requests.post(
            f"{api_url}/api/inference/batch",
            json=batch_data,
            headers=api_headers
        )
        
        # If endpoint not available or insufficient permissions, skip test
        if response.status_code == 404:
            pytest.skip("Batch inference endpoint not available")
            
        if response.status_code == 403 and "plan" in response.text.lower():
            pytest.skip("User does not have permission for batch processing")
            
        if response.status_code == 400 and "compatibility mode" in response.text.lower():
            pytest.skip("API is in compatibility mode")
        
        assert response.status_code in [200, 202], f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Validate response
        data = response.json()
        assert "task_id" in data, "Task ID missing in response"
        assert "batch_size" in data, "Batch size missing in response"
        assert data["batch_size"] == len(batch_data["texts"]), "Batch size mismatch"
        
        # Clean up the batch task after test
        cleanup_task(data["task_id"], api_headers)
    
    def test_list_tasks(self, api_url, api_headers, inference_task):
        """Test listing all tasks."""
        # Get list of tasks
        response = requests.get(
            f"{api_url}/api/tasks",
            headers=api_headers
        )
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Validate response
        data = response.json()
        assert "tasks" in data, "Tasks missing in response"
        
        # Check if our test task is in the list
        task_found = False
        if isinstance(data["tasks"], list):
            task_ids = [task.get("task_id") or task.get("id") for task in data["tasks"]]
            task_found = inference_task in task_ids
        elif isinstance(data["tasks"], dict):
            task_found = inference_task in data["tasks"]
        
        assert task_found, "Created task not found in task list"
    
    def test_cancel_task(self, api_url, api_headers, inference_task):
        """Test cancelling a task."""
        # First check if the task is in a cancellable state
        status_response = requests.get(
            f"{api_url}/api/tasks/{inference_task}",
            headers=api_headers
        )
        
        # If task already completed, skip test
        if status_response.status_code == 200:
            status_data = status_response.json()
            if status_data["status"] not in ["pending", "running"]:
                pytest.skip(f"Task already in state {status_data['status']}, cannot be cancelled")
        
        # Cancel the task
        response = requests.post(
            f"{api_url}/api/tasks/{inference_task}/cancel",
            headers=api_headers
        )
        
        # If endpoint not available, try delete instead
        if response.status_code == 404:
            response = requests.delete(
                f"{api_url}/api/tasks/{inference_task}",
                headers=api_headers
            )
        
        # If task cannot be cancelled, skip test
        if response.status_code == 400 and "not running" in response.text.lower():
            pytest.skip("Task cannot be cancelled - not in running state")
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Verify the task was cancelled
        status_response = requests.get(
            f"{api_url}/api/tasks/{inference_task}",
            headers=api_headers
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            assert status_data["status"] in ["cancelled", "deleted"], f"Task not cancelled: {status_data['status']}"
    
    def test_delete_task(self, api_url, api_headers, inference_task):
        """Test deleting a task."""
        # Delete the task
        response = requests.delete(
            f"{api_url}/api/tasks/{inference_task}",
            headers=api_headers
        )
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Verify the task was deleted
        status_response = requests.get(
            f"{api_url}/api/tasks/{inference_task}",
            headers=api_headers
        )
        
        assert status_response.status_code == 404, "Task was not deleted"