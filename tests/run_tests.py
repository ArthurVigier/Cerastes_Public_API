#!/usr/bin/env python3
"""
Script to run the API test suite with proper environment setup.
Handles setup, environment, and reporting.
"""

import argparse
import subprocess
import sys
import os
import time
import requests
from pathlib import Path

# Directory with test files
TEST_DIR = Path(__file__).parent / "tests"

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run API test suite")
    
    # Test selection options
    parser.add_argument("--auth", action="store_true", help="Run authentication tests")
    parser.add_argument("--inference", action="store_true", help="Run inference tests")
    parser.add_argument("--limits", action="store_true", help="Run usage limits tests")
    parser.add_argument("--video", action="store_true", help="Run video analysis tests")
    parser.add_argument("--transcription", action="store_true", help="Run transcription tests")
    parser.add_argument("--tasks", action="store_true", help="Run task management tests")
    parser.add_argument("--health", action="store_true", help="Run health tests")
    parser.add_argument("--subscription", action="store_true", help="Run subscription tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    # API connection options
    parser.add_argument("--api-url", type=str, help="API base URL", default="http://localhost:8000")
    parser.add_argument("--api-key", type=str, help="API key to use for tests")
    parser.add_argument("--token", type=str, help="JWT token to use for tests")
    
    # Test run options
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("--junit", action="store_true", help="Generate JUnit XML report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum retries for connection issues")
    parser.add_argument("--wait-for-api", action="store_true", help="Wait for API to be available")
    parser.add_argument("--wait-timeout", type=int, default=60, help="Timeout for waiting for API (seconds)")
    
    # Sample data options
    parser.add_argument("--sample-video", type=str, help="Path to sample video file")
    parser.add_argument("--sample-audio", type=str, help="Path to sample audio file")
    
    return parser.parse_args()

def wait_for_api(api_url, timeout=60):
    """Wait for the API to be available."""
    print(f"Waiting for API at {api_url} to be available...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"API is available! ({response.status_code})")
                return True
        except requests.RequestException as e:
            print(f"API not yet available: {e}")
        
        print(f"Retrying in 5 seconds... ({int(timeout - (time.time() - start_time))} seconds left)")
        time.sleep(5)
    
    print(f"Timed out waiting for API after {timeout} seconds")
    return False

def create_environment(args):
    """Create environment variables for the tests."""
    env = os.environ.copy()
    
    # Set API URL
    if args.api_url:
        env["API_BASE_URL"] = args.api_url
    
    # Set authentication credentials
    if args.api_key:
        env["TEST_API_KEY"] = args.api_key
    
    if args.token:
        env["TEST_TOKEN"] = args.token
    
    # Set sample file paths
    if args.sample_video:
        env["SAMPLE_VIDEO_PATH"] = args.sample_video
    
    if args.sample_audio:
        env["SAMPLE_AUDIO_PATH"] = args.sample_audio
    
    return env

def get_tests_to_run(args):
    """Determine which tests to run based on arguments."""
    tests = []
    
    if args.all or not any([
        args.auth, args.inference, args.limits, args.video, args.transcription,
        args.tasks, args.health, args.subscription, args.integration
    ]):
        # Run all tests if --all is specified or no specific test is selected
        tests = ["test_*.py"]
    else:
        # Add selected tests
        if args.auth:
            tests.append("test_auth.py")
        if args.inference:
            tests.append("test_inference.py")
        if args.limits:
            tests.append("test_limits.py")
        if args.video:
            tests.append("test_video.py")
        if args.transcription:
            tests.append("test_transcription.py")
        if args.tasks:
            tests.append("test_task.py")
        if args.health:
            tests.append("test_health.py")
        if args.subscription:
            tests.append("test_subscription.py")
        if args.integration:
            tests.append("test_integration.py")
    
    return tests

def run_tests(tests, env, args):
    """Run the selected tests."""
    pytest_args = [sys.executable, "-m", "pytest"]
    
    # Add verbosity
    if args.verbose:
        pytest_args.append("-v")
    
    # Add reporting options
    if args.html:
        pytest_args.extend(["--html=report.html", "--self-contained-html"])
    
    if args.junit:
        pytest_args.append("--junitxml=report.xml")
    
    # Add test paths
    for test in tests:
        if Path(test).exists():
            pytest_args.append(str(test))
        else:
            pytest_args.append(str(TEST_DIR / test))
    
    print(f"Running: {' '.join(pytest_args)}")
    return subprocess.run(pytest_args, env=env, check=False)

def main():
    """Main entry point."""
    args = parse_args()
    
    # Wait for API if requested
    if args.wait_for_api:
        if not wait_for_api(args.api_url, args.wait_timeout):
            return 1
    
    # Create environment
    env = create_environment(args)
    
    # Get tests to run
    tests = get_tests_to_run(args)
    if not tests:
        print("No tests selected")
        return 1
    
    # Run tests with retries for connection issues
    for attempt in range(1, args.max_retries + 1):
        try:
            print(f"Test attempt {attempt}/{args.max_retries}")
            start_time = time.time()
            result = run_tests(tests, env, args)
            execution_time = time.time() - start_time
            
            print(f"\n=== Test Results ===")
            print(f"Execution time: {execution_time:.2f} seconds")
            
            if result.returncode == 0:
                print("\033[92mAll tests passed!\033[0m")
                return 0
            else:
                print(f"\033[91mSome tests failed. Exit code: {result.returncode}\033[0m")
                
                # Only retry on connection issues (exit code 5 is typically connection issues)
                if result.returncode != 5 or attempt == args.max_retries:
                    return result.returncode
                
                print(f"Retrying in 5 seconds...")
                time.sleep(5)
        except KeyboardInterrupt:
            print("\nTests interrupted by user")
            return 130
    
    return 1

if __name__ == "__main__":
    sys.exit(main())