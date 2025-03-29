"""
Tests for video analysis functionality
------------------------------------
This module tests the video analysis API including upload,
manipulation analysis, and non-verbal analysis.
"""

import pytest
import requests
import os
import io
import time
from pathlib import Path


class TestVideo:
    """Test class for video analysis endpoints."""
    
    @pytest.fixture(scope="function")
    def sample_video_file(self, sample_video_path=None):
        """Create or get a sample video file for testing."""
        if sample_video_path and os.path.exists(sample_video_path):
            return open(sample_video_path, "rb")
        else:
            # Create a minimal MP4 file for testing
            fake_mp4 = io.BytesIO()
            # MP4 file signature
            fake_mp4.write(b'\x00\x00\x00\x18\x66\x74\x79\x70\x6D\x70\x34\x32')
            # Additional data
            fake_mp4.write(b'\x00' * 1024)
            fake_mp4.seek(0)
            return fake_mp4
    
    @pytest.fixture(scope="function")
    def uploaded_video(self, api_url, api_headers, sample_video_file):
        """Upload a sample video file and return its path."""
        try:
            files = {
                "file": ("test_video.mp4", sample_video_file, "video/mp4")
            }
            
            response = requests.post(
                f"{api_url}/api/video/upload",
                headers=api_headers,
                files=files
            )
            
            # If endpoint doesn't exist, skip test
            if response.status_code == 404:
                pytest.skip("Video upload endpoint not available")
            
            assert response.status_code == 200, f"Upload failed: {response.status_code}, {response.text}"
            
            data = response.json()
            assert "video_path" in data, "No video path in response"
            
            yield data["video_path"]
            
            # No cleanup needed as the server should handle temporary files
            
        finally:
            # Close the file if it's a real file
            if hasattr(sample_video_file, 'close'):
                sample_video_file.close()
    
    @pytest.fixture(scope="function")
    def manipulation_task(self, api_url, api_headers, uploaded_video, cleanup_task):
        """Create a manipulation analysis task and yield its ID."""
        # Prepare manipulation analysis data
        analysis_data = {
            "video_path": uploaded_video,
            "transcribe": True,
            "diarize": True,
            "language": "fr"
        }
        
        # Start manipulation analysis
        response = requests.post(
            f"{api_url}/api/video/manipulation-analysis",
            json=analysis_data,
            headers=api_headers
        )
        
        # If endpoint doesn't exist or service is unavailable, skip test
        if response.status_code == 404:
            pytest.skip("Manipulation analysis endpoint not available")
            
        if response.status_code == 503:
            pytest.skip("Manipulation analysis service not available")
        
        assert response.status_code in [200, 202], f"Analysis failed: {response.status_code}, {response.text}"
        
        data = response.json()
        assert "task_id" in data, "No task_id in response"
        
        task_id = data["task_id"]
        yield task_id
        
        # Clean up after test
        cleanup_task(task_id, api_headers)
    
    @pytest.fixture(scope="function")
    def nonverbal_task(self, api_url, api_headers, uploaded_video, cleanup_task):
        """Create a non-verbal analysis task and yield its ID."""
        # Prepare non-verbal analysis data
        analysis_data = {
            "video_path": uploaded_video,
            "extract_frames": True,
            "frame_count": 32,
            "analyze_facial_expressions": True
        }
        
        # Start non-verbal analysis
        response = requests.post(
            f"{api_url}/api/video/nonverbal-analysis",
            json=analysis_data,
            headers=api_headers
        )
        
        # If endpoint doesn't exist or service is unavailable, skip test
        if response.status_code == 404:
            pytest.skip("Non-verbal analysis endpoint not available")
            
        if response.status_code == 503:
            pytest.skip("Non-verbal analysis service not available")
        
        assert response.status_code in [200, 202], f"Analysis failed: {response.status_code}, {response.text}"
        
        data = response.json()
        assert "task_id" in data, "No task_id in response"
        
        task_id = data["task_id"]
        yield task_id
        
        # Clean up after test
        cleanup_task(task_id, api_headers)
    
    def test_upload_video(self, api_url, api_headers, sample_video_file):
        """Test uploading a video file."""
        files = {
            "file": ("test_video.mp4", sample_video_file, "video/mp4")
        }
        
        response = requests.post(
            f"{api_url}/api/video/upload",
            headers=api_headers,
            files=files
        )
        
        # If endpoint doesn't exist, skip test
        if response.status_code == 404:
            pytest.skip("Video upload endpoint not available")
        
        assert response.status_code == 200, f"Upload failed: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "video_path" in data, "No video path in response"
        assert "duration" in data, "No duration in response"
    
    def test_video_manipulation_analysis(self, api_url, api_headers, uploaded_video):
        """Test starting a video manipulation analysis."""
        # Prepare manipulation analysis data
        analysis_data = {
            "video_path": uploaded_video,
            "transcribe": True,
            "diarize": True,
            "language": "fr"
        }
        
        # Start manipulation analysis
        response = requests.post(
            f"{api_url}/api/video/manipulation-analysis",
            json=analysis_data,
            headers=api_headers
        )
        
        # If endpoint doesn't exist, skip test
        if response.status_code == 404:
            pytest.skip("Manipulation analysis endpoint not available")
            
        # If service is unavailable, skip test
        if response.status_code == 503:
            pytest.skip("Manipulation analysis service not available")
        
        assert response.status_code in [200, 202], f"Analysis failed: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "task_id" in data, "No task_id in response"
        assert "status" in data, "No status in response"
        assert data["status"] == "pending", f"Expected status 'pending', got '{data['status']}'"
    
    def test_video_nonverbal_analysis(self, api_url, api_headers, uploaded_video):
        """Test starting a non-verbal analysis."""
        # Prepare non-verbal analysis data
        analysis_data = {
            "video_path": uploaded_video,
            "extract_frames": True,
            "frame_count": 32,
            "analyze_facial_expressions": True
        }
        
        # Start non-verbal analysis
        response = requests.post(
            f"{api_url}/api/video/nonverbal-analysis",
            json=analysis_data,
            headers=api_headers
        )
        
        # If endpoint doesn't exist, skip test
        if response.status_code == 404:
            pytest.skip("Non-verbal analysis endpoint not available")
            
        # If service is unavailable, skip test
        if response.status_code == 503:
            pytest.skip("Non-verbal analysis service not available")
        
        assert response.status_code in [200, 202], f"Analysis failed: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "task_id" in data, "No task_id in response"
        assert "status" in data, "No status in response"
        assert data["status"] == "pending", f"Expected status 'pending', got '{data['status']}'"
    
    def test_get_manipulation_analysis_status(self, api_url, api_headers, manipulation_task):
        """Test retrieving the status of a manipulation analysis task."""
        response = requests.get(
            f"{api_url}/api/video/tasks/{manipulation_task}",
            headers=api_headers
        )
        
        # If endpoint doesn't exist, try alternative
        if response.status_code == 404:
            response = requests.get(
                f"{api_url}/api/tasks/{manipulation_task}",
                headers=api_headers
            )
            
            # If that also fails, skip test
            if response.status_code == 404:
                pytest.skip("No task status endpoint available")
        
        assert response.status_code == 200, f"Status check failed: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "status" in data, "No status in response"
        assert "progress" in data, "No progress in response"
        assert data["status"] in ["pending", "running", "completed", "failed"], f"Invalid status: {data['status']}"
    
    def test_get_nonverbal_analysis_status(self, api_url, api_headers, nonverbal_task):
        """Test retrieving the status of a non-verbal analysis task."""
        response = requests.get(
            f"{api_url}/api/video/tasks/{nonverbal_task}",
            headers=api_headers
        )
        
        # If endpoint doesn't exist, try alternative
        if response.status_code == 404:
            response = requests.get(
                f"{api_url}/api/tasks/{nonverbal_task}",
                headers=api_headers
            )
            
            # If that also fails, skip test
            if response.status_code == 404:
                pytest.skip("No task status endpoint available")
        
        assert response.status_code == 200, f"Status check failed: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "status" in data, "No status in response"
        assert "progress" in data, "No progress in response"
        assert data["status"] in ["pending", "running", "completed", "failed"], f"Invalid status: {data['status']}"
    
    def test_wait_for_manipulation_analysis(self, api_url, api_headers, manipulation_task, wait_for_task):
        """Test waiting for a manipulation analysis task to complete."""
        # Wait for the task to complete with reduced timeout for testing
        result = wait_for_task(
            manipulation_task,
            api_headers,
            endpoint="/api/video/tasks/{task_id}",
            max_retries=6,
            delay=5
        )
        
        # If first endpoint fails, try standard endpoint
        if result is None:
            result = wait_for_task(
                manipulation_task,
                api_headers,
                max_retries=6,
                delay=5
            )
        
        # If task didn't complete in time, skip this test
        if result is None:
            pytest.skip(f"Task {manipulation_task} did not complete in the allotted time")
        
        # Verify task completed successfully
        assert result["status"] == "completed", f"Task ended with status {result['status']}"
        
        # Verify results structure
        assert "results" in result, "No results in response"
        results = result["results"]
        assert isinstance(results, dict), "Results should be a dictionary"
    
    def test_wait_for_nonverbal_analysis(self, api_url, api_headers, nonverbal_task, wait_for_task):
        """Test waiting for a non-verbal analysis task to complete."""
        # Wait for the task to complete with reduced timeout for testing
        result = wait_for_task(
            nonverbal_task,
            api_headers,
            endpoint="/api/video/tasks/{task_id}",
            max_retries=6,
            delay=5
        )
        
        # If first endpoint fails, try standard endpoint
        if result is None:
            result = wait_for_task(
                nonverbal_task,
                api_headers,
                max_retries=6,
                delay=5
            )
        
        # If task didn't complete in time, skip this test
        if result is None:
            pytest.skip(f"Task {nonverbal_task} did not complete in the allotted time")
        
        # Verify task completed successfully
        assert result["status"] == "completed", f"Task ended with status {result['status']}"
        
        # Verify results structure
        assert "results" in result, "No results in response"
        results = result["results"]
        assert isinstance(results, dict), "Results should be a dictionary"
    
    def test_get_all_video_tasks(self, api_url, api_headers, manipulation_task):
        """Test listing all video tasks."""
        response = requests.get(
            f"{api_url}/api/video/tasks",
            headers=api_headers
        )
        
        # If endpoint doesn't exist, skip test
        if response.status_code == 404:
            pytest.skip("Video tasks listing endpoint not available")
        
        assert response.status_code == 200, f"Tasks listing failed: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "tasks" in data, "No tasks in response"
        tasks = data["tasks"]
        assert isinstance(tasks, list), "Tasks should be a list"
        
        # Find our test task
        task_ids = [task.get("id") for task in tasks]
        assert manipulation_task in task_ids, "Created task not found in task list"
    
    def test_delete_video_task(self, api_url, api_headers, manipulation_task):
        """Test deleting a video task."""
        # Delete the task
        response = requests.delete(
            f"{api_url}/api/video/tasks/{manipulation_task}",
            headers=api_headers
        )
        
        # If endpoint doesn't exist, try alternative
        if response.status_code == 404:
            response = requests.delete(
                f"{api_url}/api/tasks/{manipulation_task}",
                headers=api_headers
            )
            
            # If that also fails, skip test
            if response.status_code == 404:
                pytest.skip("No task deletion endpoint available")
        
        assert response.status_code == 200, f"Task deletion failed: {response.status_code}, {response.text}"
        
        # Verify deletion
        response = requests.get(
            f"{api_url}/api/video/tasks/{manipulation_task}",
            headers=api_headers
        )
        
        assert response.status_code == 404, "Task was not deleted"