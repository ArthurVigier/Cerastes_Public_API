"""
Tests for API usage limits and restrictions
-----------------------------------------
This module tests the API usage limits including rate limits,
text length restrictions, and plan-based feature restrictions.
"""

import pytest
import requests
import uuid
import time
from typing import Dict, Any


class TestLimits:
    """Test class for API usage limits."""
    
    def test_text_length_limit(self, api_url, api_headers):
        """Test the maximum text length limit."""
        # Get a large text for testing by repeating a paragraph
        base_text = "This is a sample paragraph for testing text length limits. It contains multiple sentences with different words and punctuation. The API should enforce length restrictions based on the user's subscription level. "
        
        # Generate texts of different lengths to find the limit
        texts = {
            "small": base_text * 10,      # Approx 1,000 chars
            "medium": base_text * 100,    # Approx 10,000 chars
            "large": base_text * 500,     # Approx 50,000 chars
            "very_large": base_text * 1000 # Approx 100,000 chars
        }
        
        # Test each text size
        limit_found = False
        max_allowed_length = 0
        
        for size, text in texts.items():
            print(f"Testing {size} text ({len(text)} characters)")
            
            # Prepare inference data
            inference_data = {
                "text": text,
                "use_segmentation": True,
                "max_new_tokens": 100
            }
            
            # Start inference task
            response = requests.post(
                f"{api_url}/api/inference/start",
                json=inference_data,
                headers=api_headers
            )
            
            # If we get a 403 Forbidden with a message about text length, we've found the limit
            if response.status_code == 403 and any(keyword in response.text.lower() for keyword in ["length", "text", "limit", "characters"]):
                limit_found = True
                print(f"Length limit found: text with {len(text)} characters was rejected")
                break
                
            # If we get a successful response, the text length is allowed
            if response.status_code in [200, 202]:
                max_allowed_length = len(text)
                
                # Clean up the task
                data = response.json()
                task_id = data.get("task_id") or data.get("id")
                if task_id:
                    try:
                        requests.delete(f"{api_url}/api/tasks/{task_id}", headers=api_headers)
                    except:
                        pass
        
        # If we tested all sizes without finding a limit, note that
        if not limit_found and max_allowed_length > 0:
            print(f"No length limit found up to {max_allowed_length} characters")
        
        # This test doesn't necessarily fail if no limit is found
        # The API could have high limits or handle text segmentation automatically
    
    def test_token_count_limit(self, api_url, api_headers):
        """Test the maximum token count limit."""
        # Test different token values
        token_values = [100, 500, 1000, 2000, 5000, 10000]
        
        limit_found = False
        max_allowed_tokens = 0
        
        for tokens in token_values:
            print(f"Testing {tokens} tokens")
            
            # Prepare inference data
            inference_data = {
                "text": "This is a test for token count limits.",
                "use_segmentation": True,
                "max_new_tokens": tokens
            }
            
            # Start inference task
            response = requests.post(
                f"{api_url}/api/inference/start",
                json=inference_data,
                headers=api_headers
            )
            
            # If we get a 403 Forbidden with a message about token count, we've found the limit
            if response.status_code == 403 and any(keyword in response.text.lower() for keyword in ["token", "count", "limit"]):
                limit_found = True
                print(f"Token limit found: {tokens} tokens was rejected")
                break
                
            # If we get a successful response, the token count is allowed
            if response.status_code in [200, 202]:
                max_allowed_tokens = tokens
                
                # Clean up the task
                data = response.json()
                task_id = data.get("task_id") or data.get("id")
                if task_id:
                    try:
                        requests.delete(f"{api_url}/api/tasks/{task_id}", headers=api_headers)
                    except:
                        pass
        
        # If we tested all values without finding a limit, note that
        if not limit_found and max_allowed_tokens > 0:
            print(f"No token limit found up to {max_allowed_tokens} tokens")
    
    def test_batch_processing_restriction(self, api_url, api_headers):
        """Test if batch processing is restricted based on subscription level."""
        # Prepare batch data
        batch_data = {
            "texts": [
                "This is the first text for batch processing test.",
                "This is the second text for batch processing test."
            ],
            "use_segmentation": True,
            "max_new_tokens": 100
        }
        
        # Start batch inference
        response = requests.post(
            f"{api_url}/api/inference/batch",
            json=batch_data,
            headers=api_headers
        )
        
        # If endpoint doesn't exist, skip test
        if response.status_code == 404:
            pytest.skip("Batch processing endpoint not available")
        
        # Check if batch processing is restricted
        if response.status_code == 403 and any(keyword in response.text.lower() for keyword in ["batch", "plan", "subscription", "upgrade"]):
            print("Batch processing is restricted to higher subscription levels")
        elif response.status_code in [200, 202]:
            print("Batch processing is allowed with current subscription level")
            
            # Clean up the task
            data = response.json()
            task_id = data.get("task_id") or data.get("id")
            if task_id:
                try:
                    requests.delete(f"{api_url}/api/tasks/{task_id}", headers=api_headers)
                except:
                    pass
        else:
            print(f"Unexpected response: {response.status_code}, {response.text}")
    
    def test_concurrent_requests(self, api_url, api_headers):
        """Test concurrent request limits."""
        # Number of concurrent requests to test
        num_requests = 5
        
        # Prepare inference data
        inference_data = {
            "text": "This is a test for concurrent request limits.",
            "use_segmentation": True,
            "max_new_tokens": 100
        }
        
        # Start multiple requests simultaneously
        tasks = []
        for i in range(num_requests):
            response = requests.post(
                f"{api_url}/api/inference/start",
                json=inference_data,
                headers=api_headers
            )
            
            if response.status_code in [200, 202]:
                data = response.json()
                task_id = data.get("task_id") or data.get("id")
                if task_id:
                    tasks.append(task_id)
                    print(f"Started task {i+1}/{num_requests}: {task_id}")
            elif response.status_code == 429:
                print(f"Request {i+1}/{num_requests} was rate limited")
                break
            elif response.status_code == 403 and any(keyword in response.text.lower() for keyword in ["concurrent", "limit", "simultaneous"]):
                print(f"Request {i+1}/{num_requests} exceeded concurrent request limit")
                break
            else:
                print(f"Request {i+1}/{num_requests} failed: {response.status_code}, {response.text}")
        
        # Clean up tasks
        for task_id in tasks:
            try:
                requests.delete(f"{api_url}/api/tasks/{task_id}", headers=api_headers)
            except:
                pass
        
        # No assertions - this is an informational test
    
    def test_rate_limits(self, api_url, api_headers):
        """Test API rate limits."""
        # Number of requests to test
        num_requests = 20
        
        # Track successful and rate-limited requests
        successful = 0
        rate_limited = 0
        
        # Make multiple requests in quick succession
        for i in range(num_requests):
            # Simple health check to avoid creating resources
            response = requests.get(f"{api_url}/health", headers=api_headers)
            
            if response.status_code == 200:
                successful += 1
            elif response.status_code == 429:
                rate_limited += 1
                print(f"Request {i+1}/{num_requests} was rate limited")
                # If we hit a rate limit, wait a bit before continuing
                time.sleep(1)
            else:
                print(f"Request {i+1}/{num_requests} failed: {response.status_code}")
        
        print(f"Completed {successful}/{num_requests} requests successfully")
        print(f"Rate limited: {rate_limited}/{num_requests} requests")
        
        # No assertions - this is an informational test
    
    def test_advanced_model_access(self, api_url, api_headers):
        """Test access to advanced models based on subscription level."""
        # List of model names to test, from basic to advanced
        models = ["base", "medium", "large", "advanced"]
        
        results = {}
        
        for model in models:
            print(f"Testing access to model: {model}")
            
            # Prepare inference data
            inference_data = {
                "text": "This is a test for model access restrictions.",
                "use_segmentation": True,
                "max_new_tokens": 100,
                "model": model
            }
            
            # Start inference task
            response = requests.post(
                f"{api_url}/api/inference/start",
                json=inference_data,
                headers=api_headers
            )
            
            # Check if model is restricted
            if response.status_code == 403 and any(keyword in response.text.lower() for keyword in ["model", "advanced", "plan", "subscription", "upgrade"]):
                print(f"Model '{model}' is restricted to higher subscription levels")
                results[model] = "restricted"
            elif response.status_code in [200, 202]:
                print(f"Model '{model}' is accessible with current subscription level")
                results[model] = "accessible"
                
                # Clean up the task
                data = response.json()
                task_id = data.get("task_id") or data.get("id")
                if task_id:
                    try:
                        requests.delete(f"{api_url}/api/tasks/{task_id}", headers=api_headers)
                    except:
                        pass
            elif response.status_code == 404 or response.status_code == 400 and "model" in response.text.lower():
                print(f"Model '{model}' does not exist or is invalid")
                results[model] = "not found"
            else:
                print(f"Unexpected response for model '{model}': {response.status_code}, {response.text}")
                results[model] = "error"
        
        # Print summary
        print("\nModel access summary:")
        for model, status in results.items():
            print(f"- {model}: {status}")