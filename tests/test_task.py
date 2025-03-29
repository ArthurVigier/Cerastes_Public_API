"""
Tests for task management functionality
-------------------------------------
This module tests the task API including creating, listing,
retrieving, and cancelling tasks.
"""

import pytest
import requests
import time
import uuid
from typing import Dict, Any


class TestTask:
    """Test class for task management endpoints."""
    
    @pytest.fixture(scope="function")
    def sample_task(self, api_url, api_headers, cleanup_task):
        """Create a simple task for testing."""
        # Create a basic inference task
        inference_data = {
            "text": "This is a test for task management.",
            "use_segmentation": True,
            "max_new_tokens": 100
        }
        
        # Start inference task
        response = requests.post(
            f"{api_url}/api/inference/start",
            json=inference_data,
            headers=api_headers
        )
        
        # Handle different endpoint formats
        if response.status_code == 404:
            response = requests.post(
                f"{api_url}/api/inference",
                json=inference_data,
                headers=api_headers
            )
        
        # If we can't create a task, skip the test
        if response.status_code not in [200, 202]:
            pytest.skip(f"Could not create test task: {response.status_code}, {response.text}")
        
        # Parse response
        data = response.json()
        task_id = data.get("task_id") or data.get("id")
        
        # Yield task ID
        yield task_id
        
        # Clean up after test
        cleanup_task(task_id, api_headers)
    
    @pytest.fixture(scope="function")
    def batch_task(self, api_url, api_headers, cleanup_task):
        """Create a batch task for testing if supported."""
        # Create batch inference task
        batch_data = {
            "texts": [
                "First test text for batch task.",
                "Second test text for batch task."
            ],
            "use_segmentation": True,
            "max_new_tokens": 100
        }
        
        # Try to start batch inference
        response = requests.post(
            f"{api_url}/api/inference/batch",
            json=batch_data,
            headers=api_headers
        )
        
        # If batch processing is not available, skip
        if response.status_code in [403, 404]:
            pytest.skip("Batch processing not available")
        
        if response.status_code not in [200, 202]:
            pytest.skip(f"Could not create batch task: {response.status_code}, {response.text}")
        
        # Parse response
        data = response.json()
        task_id = data.get("task_id") or data.get("id")
        
        # Yield task ID
        yield task_id
        
        # Clean up after test
        cleanup_task(task_id, api_headers)
    
    def test_get_specific_task(self, api_url, api_headers, sample_task):
        """Test retrieving a specific task."""
        response = requests.get(
            f"{api_url}/api/tasks/{sample_task}",
            headers=api_headers
        )
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response data
        data = response.json()
        assert "task_id" in data or "id" in data, "Task ID missing in response"
        task_id = data.get("task_id") or data.get("id")
        assert task_id == sample_task, "Task ID mismatch"
        assert "status" in data, "Status missing in response"
        assert "type" in data, "Type missing in response"
        assert "created_at" in data, "Created at missing in response"
    
    def test_get_nonexistent_task(self, api_url, api_headers):
        """Test retrieving a task that doesn't exist."""
        # Generate a random task ID
        fake_task_id = str(uuid.uuid4())
        
        response = requests.get(
            f"{api_url}/api/tasks/{fake_task_id}",
            headers=api_headers
        )
        
        assert response.status_code == 404, f"Expected 404, got: {response.status_code}, {response.text}"
    
    def test_list_all_tasks(self, api_url, api_headers, sample_task):
        """Test listing all tasks."""
        response = requests.get(
            f"{api_url}/api/tasks",
            headers=api_headers
        )
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response data
        data = response.json()
        assert "tasks" in data, "Tasks missing in response"
        
        # Verify task data
        tasks = data["tasks"]
        assert isinstance(tasks, (list, dict)), "Tasks should be a list or dict"
        
        # Find our test task
        task_found = False
        if isinstance(tasks, list):
            for task in tasks:
                task_id = task.get("task_id") or task.get("id")
                if task_id == sample_task:
                    task_found = True
                    break
        else:  # tasks is a dict
            task_found = sample_task in tasks
        
        assert task_found, "Created task not found in task list"
    
    def test_filter_tasks_by_status(self, api_url, api_headers, sample_task):
        """Test filtering tasks by status."""
        # Get current status of our task
        response = requests.get(
            f"{api_url}/api/tasks/{sample_task}",
            headers=api_headers
        )
        
        assert response.status_code == 200
        task_data = response.json()
        task_status = task_data["status"]
        
        # Filter by that status
        response = requests.get(
            f"{api_url}/api/tasks?status={task_status}",
            headers=api_headers
        )
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check filtered data
        data = response.json()
        assert "tasks" in data, "Tasks missing in response"
        
        # Verify all tasks have the correct status
        tasks = data["tasks"]
        if isinstance(tasks, list) and tasks:
            for task in tasks:
                assert task["status"] == task_status, f"Task has incorrect status: {task['status']}"
        elif isinstance(tasks, dict) and tasks:
            for task_id, task in tasks.items():
                assert task["status"] == task_status, f"Task has incorrect status: {task['status']}"
    
    def test_filter_tasks_by_type(self, api_url, api_headers, sample_task):
        """Test filtering tasks by type."""
        # Get type of our task
        response = requests.get(
            f"{api_url}/api/tasks/{sample_task}",
            headers=api_headers
        )
        
        assert response.status_code == 200
        task_data = response.json()
        task_type = task_data["type"]
        
        # Filter by that type
        response = requests.get(
            f"{api_url}/api/tasks?task_type={task_type}",
            headers=api_headers
        )
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check filtered data
        data = response.json()
        assert "tasks" in data, "Tasks missing in response"
        
        # Verify all tasks have the correct type
        tasks = data["tasks"]
        if isinstance(tasks, list) and tasks:
            for task in tasks:
                assert task["type"] == task_type, f"Task has incorrect type: {task['type']}"
        elif isinstance(tasks, dict) and tasks:
            for task_id, task in tasks.items():
                assert task["type"] == task_type, f"Task has incorrect type: {task['type']}"
    
    def test_pagination(self, api_url, api_headers):
        """Test task pagination."""
        # Get first page with limit of 1
        response = requests.get(
            f"{api_url}/api/tasks?limit=1&offset=0",
            headers=api_headers
        )
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check first page
        data1 = response.json()
        assert "tasks" in data1, "Tasks missing in response"
        tasks1 = data1["tasks"]
        
        # If no tasks, skip the test
        if (isinstance(tasks1, list) and not tasks1) or (isinstance(tasks1, dict) and not tasks1):
            pytest.skip("No tasks available for pagination testing")
        
        # Verify limit is respected
        if isinstance(tasks1, list):
            assert len(tasks1) <= 1, "More than 1 task returned with limit=1"
        else:  # tasks is a dict
            assert len(tasks1) <= 1, "More than 1 task returned with limit=1"
        
        # Get second page
        response = requests.get(
            f"{api_url}/api/tasks?limit=1&offset=1",
            headers=api_headers
        )
        
        assert response.status_code == 200
        
        # Check second page
        data2 = response.json()
        assert "tasks" in data2, "Tasks missing in response"
        tasks2 = data2["tasks"]
        
        # Skip if second page is empty
        if (isinstance(tasks2, list) and not tasks2) or (isinstance(tasks2, dict) and not tasks2):
            pytest.skip("No tasks available on second page")
        
        # Verify pages are different
        if isinstance(tasks1, list) and isinstance(tasks2, list):
            first_id = tasks1[0].get("task_id") or tasks1[0].get("id")
            second_id = tasks2[0].get("task_id") or tasks2[0].get("id")
            assert first_id != second_id, "First and second page contain the same task"
        elif isinstance(tasks1, dict) and isinstance(tasks2, dict):
            task_ids1 = set(tasks1.keys())
            task_ids2 = set(tasks2.keys())
            assert not task_ids1.intersection(task_ids2), "First and second page contain the same task"
    
    def test_cancel_task(self, api_url, api_headers, sample_task):
        """Test cancelling a task."""
        # Check if task is running
        response = requests.get(
            f"{api_url}/api/tasks/{sample_task}",
            headers=api_headers
        )
        
        assert response.status_code == 200
        task_data = response.json()
        
        # Skip if task is already completed
        if task_data["status"] not in ["pending", "running"]:
            pytest.skip(f"Task is already in state {task_data['status']} and cannot be cancelled")
        
        # Cancel the task
        response = requests.post(
            f"{api_url}/api/tasks/{sample_task}/cancel",
            headers=api_headers
        )
        
        # Try alternative endpoint if needed
        if response.status_code == 404:
            response = requests.delete(
                f"{api_url}/api/tasks/{sample_task}",
                headers=api_headers
            )
        
        # Check if cancellation is supported
        if response.status_code == 400 and "not running" in response.text.lower():
            pytest.skip("Task cannot be cancelled - not in running state")
        
        assert response.status_code in [200, 202], f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Verify cancellation
        response = requests.get(
            f"{api_url}/api/tasks/{sample_task}",
            headers=api_headers
        )
        
        # Task might be deleted
        if response.status_code == 404:
            return
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["cancelled", "deleted"], f"Task not cancelled correctly: {data['status']}"
    
    def test_retry_failed_task(self, api_url, api_headers):
        """Test retrying a failed task if supported."""
        # Find a failed task
        response = requests.get(
            f"{api_url}/api/tasks?status=failed",
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Get failed task ID
        failed_task_id = None
        tasks = data.get("tasks", [])
        
        if isinstance(tasks, list):
            for task in tasks:
                if task.get("status") == "failed":
                    failed_task_id = task.get("task_id") or task.get("id")
                    break
        elif isinstance(tasks, dict):
            for task_id, task in tasks.items():
                if task.get("status") == "failed":
                    failed_task_id = task_id
                    break
        
        if not failed_task_id:
            pytest.skip("No failed tasks found")
        
        # Try to retry the task
        response = requests.post(
            f"{api_url}/api/tasks/{failed_task_id}/retry",
            headers=api_headers
        )
        
        # Skip if retry not supported
        if response.status_code == 404:
            pytest.skip("Retry endpoint not available")
        
        assert response.status_code in [200, 202], f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response format
        data = response.json()
        assert "task_id" in data or "id" in data, "No task ID in response"
    
    def test_delete_task(self, api_url, api_headers, sample_task):
        """Test deleting a task."""
        # Delete the task
        response = requests.delete(
            f"{api_url}/api/tasks/{sample_task}",
            headers=api_headers
        )
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Verify deletion
        response = requests.get(
            f"{api_url}/api/tasks/{sample_task}",
            headers=api_headers
        )
        
        assert response.status_code == 404, "Task was not deleted"