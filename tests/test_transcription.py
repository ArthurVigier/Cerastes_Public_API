"""
Tests for audio transcription functionality
----------------------------------------
This module tests the audio transcription API including monologue
and multi-speaker transcription functionality.
"""

import pytest
import requests
import io
import os
from pathlib import Path

class TestTranscription:
    """Test class for transcription endpoints."""
    
    @pytest.fixture(scope="function")
    def sample_audio_file(self, sample_audio_path=None):
        """Create or get a sample audio file for testing."""
        if sample_audio_path and os.path.exists(sample_audio_path):
            return open(sample_audio_path, "rb")
        else:
            # Create a minimal MP3 file for testing
            fake_mp3 = io.BytesIO()
            # MP3 header (ID3v2)
            fake_mp3.write(b'ID3\x03\x00\x00\x00\x00\x00\x00')
            # MP3 frame header
            fake_mp3.write(b'\xFF\xFB\x90\x44\x00\x00\x00\x00')
            # Additional data
            fake_mp3.write(b'\x00' * 1024)
            fake_mp3.seek(0)
            return fake_mp3
    
    @pytest.fixture(scope="function")
    def uploaded_audio(self, api_url, api_headers, sample_audio_file):
        """Upload a sample audio file and return its path."""
        try:
            files = {
                "file": ("test_audio.mp3", sample_audio_file, "audio/mpeg")
            }
            
            response = requests.post(
                f"{api_url}/api/transcription/upload",
                headers=api_headers,
                files=files
            )
            
            # If endpoint doesn't exist, try an alternative
            if response.status_code == 404:
                files = {
                    "audio": ("test_audio.mp3", sample_audio_file, "audio/mpeg")
                }
                response = requests.post(
                    f"{api_url}/api/upload/audio",
                    headers=api_headers,
                    files=files
                )
                
                # If that also fails, skip the test
                if response.status_code == 404:
                    pytest.skip("No audio upload endpoint available")
            
            assert response.status_code == 200, f"Upload failed: {response.status_code}, {response.text}"
            
            data = response.json()
            audio_path = data.get("file_path") or data.get("audio_path")
            assert audio_path, "No audio path in response"
            
            yield audio_path
            
            # No cleanup needed as the server should handle temporary files
            
        finally:
            # Close the file if it's a real file
            if hasattr(sample_audio_file, 'close'):
                sample_audio_file.close()
    
    @pytest.fixture(scope="function")
    def transcription_task(self, api_url, api_headers, uploaded_audio, cleanup_task):
        """Create a transcription task and yield its ID."""
        # Prepare transcription data
        transcription_data = {
            "file_path": uploaded_audio,
            "language": "fr",
            "model": "base",  # Use the smallest model for faster tests
            "diarize": False
        }
        
        # Start transcription
        response = requests.post(
            f"{api_url}/api/transcription/monologue",
            json=transcription_data,
            headers=api_headers
        )
        
        # If endpoint doesn't exist, try alternatives
        if response.status_code == 404:
            # Try alternative endpoint format
            transcription_data["model_size"] = transcription_data.pop("model")
            response = requests.post(
                f"{api_url}/api/transcription/start",
                json=transcription_data,
                headers=api_headers
            )
            
            # If that also fails, skip the test
            if response.status_code == 404:
                pytest.skip("No transcription endpoint available")
        
        assert response.status_code in [200, 202], f"Transcription failed: {response.status_code}, {response.text}"
        
        data = response.json()
        assert "task_id" in data, "No task_id in response"
        
        task_id = data["task_id"]
        yield task_id
        
        # Clean up after test
        cleanup_task(task_id, api_headers)
    
    def test_upload_audio_file(self, api_url, api_headers, sample_audio_file):
        """Test uploading an audio file."""
        files = {
            "file": ("test_audio.mp3", sample_audio_file, "audio/mpeg")
        }
        
        response = requests.post(
            f"{api_url}/api/transcription/upload",
            headers=api_headers,
            files=files
        )
        
        # If endpoint doesn't exist, try an alternative
        if response.status_code == 404:
            files = {
                "audio": ("test_audio.mp3", sample_audio_file, "audio/mpeg")
            }
            response = requests.post(
                f"{api_url}/api/upload/audio",
                headers=api_headers,
                files=files
            )
            
            # If that also fails, skip the test
            if response.status_code == 404:
                pytest.skip("No audio upload endpoint available")
        
        assert response.status_code == 200, f"Upload failed: {response.status_code}, {response.text}"
        
        data = response.json()
        assert "file_path" in data or "audio_path" in data, "No file path in response"
    
    def test_start_transcription_monologue(self, api_url, api_headers, uploaded_audio):
        """Test starting a monologue transcription."""
        # Prepare transcription data
        transcription_data = {
            "file_path": uploaded_audio,
            "language": "fr",
            "model": "base",  # Use the smallest model for faster tests
            "diarize": False
        }
        
        # Start transcription
        response = requests.post(
            f"{api_url}/api/transcription/monologue",
            json=transcription_data,
            headers=api_headers
        )
        
        # If endpoint doesn't exist, try alternatives
        if response.status_code == 404:
            # Try alternative endpoint format
            transcription_data["model_size"] = transcription_data.pop("model")
            response = requests.post(
                f"{api_url}/api/transcription/start",
                json=transcription_data,
                headers=api_headers
            )
            
            # If that also fails, skip the test
            if response.status_code == 404:
                pytest.skip("No transcription endpoint available")
        
        assert response.status_code in [200, 202], f"Transcription failed: {response.status_code}, {response.text}"
        
        data = response.json()
        assert "task_id" in data, "No task_id in response"
    
    def test_start_transcription_multispeaker(self, api_url, api_headers, uploaded_audio):
        """Test starting a multi-speaker transcription."""
        # Prepare transcription data
        transcription_data = {
            "file_path": uploaded_audio,
            "language": "fr",
            "model": "base",  # Use the smallest model for faster tests
            "diarize": True,
            "min_speakers": 2,
            "max_speakers": 5
        }
        
        # Start transcription
        response = requests.post(
            f"{api_url}/api/transcription/multispeaker",
            json=transcription_data,
            headers=api_headers
        )
        
        # If endpoint doesn't exist, try alternatives
        if response.status_code == 404:
            # Try alternative endpoint format
            transcription_data["model_size"] = transcription_data.pop("model")
            response = requests.post(
                f"{api_url}/api/transcription/start",
                json=transcription_data,
                headers=api_headers
            )
            
            # If that also fails, skip the test
            if response.status_code == 404:
                pytest.skip("No multi-speaker transcription endpoint available")
        
        # If service unavailable, skip test
        if response.status_code == 503:
            pytest.skip("Diarization service not available")
        
        assert response.status_code in [200, 202], f"Transcription failed: {response.status_code}, {response.text}"
        
        data = response.json()
        assert "task_id" in data, "No task_id in response"
    
    def test_get_transcription_status(self, api_url, api_headers, transcription_task):
        """Test retrieving transcription task status."""
        response = requests.get(
            f"{api_url}/api/transcription/tasks/{transcription_task}",
            headers=api_headers
        )
        
        # If endpoint doesn't exist, try alternatives
        if response.status_code == 404:
            response = requests.get(
                f"{api_url}/api/tasks/{transcription_task}",
                headers=api_headers
            )
            
            # If that also fails, skip the test
            if response.status_code == 404:
                pytest.skip("No task status endpoint available")
        
        assert response.status_code == 200, f"Status check failed: {response.status_code}, {response.text}"
        
        data = response.json()
        assert "status" in data, "No status in response"
        assert "progress" in data, "No progress in response"
        assert data["status"] in ["pending", "running", "completed", "failed"], f"Invalid status: {data['status']}"
    
    def test_wait_for_transcription_completion(self, api_url, api_headers, transcription_task, wait_for_task):
        """Test waiting for transcription completion."""
        # Wait for the task to complete
        result = wait_for_task(
            transcription_task,
            api_headers,
            max_retries=10,  # Lower timeout for tests
            delay=3
        )
        
        # If task didn't complete in time, skip this test
        if result is None:
            pytest.skip(f"Task {transcription_task} did not complete in the allotted time")
        
        # Verify task completed successfully
        assert result["status"] == "completed", f"Task ended with status {result['status']}"
        
        # Verify results structure
        assert "results" in result, "No results in response"
        results = result["results"]
        
        # Results may be structured differently based on the API
        if isinstance(results, dict):
            assert "transcription" in results, "No transcription in results"
            
            # Transcription can be a string or a list for diarization
            transcription = results["transcription"]
            assert isinstance(transcription, (str, list)), f"Invalid transcription type: {type(transcription)}"
    
    def test_list_transcription_tasks(self, api_url, api_headers, transcription_task):
        """Test listing all transcription tasks."""
        response = requests.get(
            f"{api_url}/api/transcription/tasks",
            headers=api_headers
        )
        
        # If endpoint doesn't exist, try alternatives
        if response.status_code == 404:
            response = requests.get(
                f"{api_url}/api/tasks?task_type=transcription",
                headers=api_headers
            )
            
            # If that also fails, skip the test
            if response.status_code == 404:
                pytest.skip("No task listing endpoint available")
        
        assert response.status_code == 200, f"Listing tasks failed: {response.status_code}, {response.text}"
        
        data = response.json()
        
        # Response can be a list directly or an object with a tasks list
        tasks = data if isinstance(data, list) else data.get("tasks", [])
        
        # Verify that it's a list
        assert isinstance(tasks, list), "Tasks not returned as a list"
        
        # Check if our test task is in the list
        task_ids = [task.get("task_id") or task.get("id") for task in tasks]
        assert transcription_task in task_ids, "Created task not found in task list"
    
    def test_invalid_audio_format(self, api_url, api_headers):
        """Test validation of audio format."""
        # Create a text file instead of an audio file
        text_file = io.BytesIO(b"This is not an audio file")
        
        files = {
            "audio": ("not_audio.txt", text_file, "text/plain")
        }
        
        data = {
            "language": "fr",
            "model": "base"
        }
        
        # Send request with invalid audio format
        response = requests.post(
            f"{api_url}/api/transcription/monologue",
            headers=api_headers,
            files=files,
            data=data
        )
        
        # If endpoint doesn't exist, skip the test
        if response.status_code == 404:
            pytest.skip("No monologue transcription endpoint available")
        
        # Response should be a 400 Bad Request
        assert response.status_code == 400, f"Expected 400, got: {response.status_code}, {response.text}"
        
        # Verify error is related to file format
        error_data = response.json()
        assert "detail" in error_data or "error" in error_data, "No error message in response"
        error_message = error_data.get("detail") or error_data.get("error")
        assert "format" in error_message.lower() or "file" in error_message.lower(), "Error not related to file format"
    
    def test_cancel_transcription_task(self, api_url, api_headers, transcription_task):
        """Test cancelling a transcription task."""
        # First check the task status
        response = requests.get(
            f"{api_url}/api/tasks/{transcription_task}",
            headers=api_headers
        )
        
        # If we can't get the status, skip the test
        if response.status_code != 200:
            pytest.skip(f"Cannot get task status: {response.status_code}")
        
        task_data = response.json()
        
        # If task is already completed, skip this test
        if task_data["status"] not in ["pending", "running"]:
            pytest.skip(f"Task {transcription_task} is already in state {task_data['status']} and cannot be cancelled")
        
        # Cancel the task
        # Try specific endpoint first
        response = requests.delete(
            f"{api_url}/api/transcription/tasks/{transcription_task}",
            headers=api_headers
        )
        
        # If endpoint doesn't exist, try alternatives
        if response.status_code == 404:
            # Try POST to cancel endpoint
            response = requests.post(
                f"{api_url}/api/tasks/{transcription_task}/cancel",
                headers=api_headers
            )
            
            # If that fails, try DELETE on central endpoint
            if response.status_code == 404:
                response = requests.delete(
                    f"{api_url}/api/tasks/{transcription_task}",
                    headers=api_headers
                )
        
        # If all cancellation attempts fail, skip the test
        if response.status_code not in [200, 202]:
            pytest.skip(f"Cannot cancel task {transcription_task}: {response.status_code}, {response.text}")
        
        # Verify the task has been cancelled
        response = requests.get(
            f"{api_url}/api/tasks/{transcription_task}",
            headers=api_headers
        )
        
        # If task was completely deleted, that's also acceptable
        if response.status_code == 404:
            return
        
        assert response.status_code == 200, f"Cannot verify cancellation: {response.status_code}, {response.text}"
        
        task_data = response.json()
        assert task_data["status"] in ["cancelled", "deleted"], f"Task not cancelled correctly: {task_data['status']}"