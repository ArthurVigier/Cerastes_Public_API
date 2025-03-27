"""
Failover middleware for AI models.
Automatically manages failover to alternative models in case of errors,
implements retry strategies, and ensures better service availability.
"""

import json
import time
import logging
import traceback
from typing import Dict, List, Any, Optional, Callable, Tuple, Set
from collections import defaultdict
import random
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Logging configuration
logger = logging.getLogger("failover_middleware")

class FailoverConfig:
    """Configuration of failover strategies for a model type."""
    
    def __init__(
        self,
        model_type: str,
        alternatives: Dict[str, List[str]],
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        jitter: float = 0.1,
        cooldown_period: int = 300,  # 5 minutes
    ):
        """
        Initializes the failover configuration.
        
        Args:
            model_type: Model type (text, video, transcription, etc.)
            alternatives: Dictionary of alternative models by main model
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff factor
            jitter: Random variation to avoid request storms
            cooldown_period: Cooling period before retrying a failed model (seconds)
        """
        self.model_type = model_type
        self.alternatives = alternatives
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.cooldown_period = cooldown_period

class ModelStatus:
    """Availability status of a model."""
    
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.available = True
        self.failure_count = 0
        self.last_failure_time = 0
        self.recovery_count = 0
        self.cumulative_errors = 0
    
    def mark_failure(self) -> None:
        """Marks the model as having failed."""
        self.available = False
        self.failure_count += 1
        self.cumulative_errors += 1
        self.last_failure_time = time.time()
    
    def mark_success(self) -> None:
        """Marks the model as functional."""
        if not self.available:
            self.recovery_count += 1
        self.available = True
        self.failure_count = 0
    
    def should_retry(self, cooldown_period: int) -> bool:
        """Checks if the model should be retried after a cooling period."""
        if self.available:
            return True
        
        # Calculate a progressive cooldown based on the number of failures
        adjusted_cooldown = cooldown_period * min(5, self.failure_count)
        
        # Check if the cooling time has elapsed
        return (time.time() - self.last_failure_time) > adjusted_cooldown
    
    def __str__(self) -> str:
        return (f"ModelStatus(model_id={self.model_id}, available={self.available}, "
                f"failures={self.failure_count}, recoveries={self.recovery_count}, "
                f"total_errors={self.cumulative_errors})")

class FailoverManager:
    """Centralized manager for failover strategies."""
    
    def __init__(self):
        # Configurations by model type
        self.configs: Dict[str, FailoverConfig] = {}
        
        # Model status
        self.model_status: Dict[str, ModelStatus] = {}
        
        # Failover history for analysis
        self.failover_history: List[Dict[str, Any]] = []
        self.history_max_size = 100
        
        # Metrics counters
        self.metrics = {
            "total_failovers": 0,
            "successful_failovers": 0,
            "failed_failovers": 0,
            "models_recovered": 0
        }
    
    def register_config(self, config: FailoverConfig) -> None:
        """Registers a failover configuration."""
        self.configs[config.model_type] = config
        
        # Initialize status for all models in this configuration
        for primary, alternatives in config.alternatives.items():
            self._ensure_model_status(primary)
            for alt in alternatives:
                self._ensure_model_status(alt)
    
    def _ensure_model_status(self, model_id: str) -> None:
        """Ensures a status exists for the given model."""
        if model_id not in self.model_status:
            self.model_status[model_id] = ModelStatus(model_id)
    
    def get_alternative_model(self, model_type: str, original_model: str) -> Optional[str]:
        """
        Gets an available alternative model for the given model.
        
        Args:
            model_type: Model type (text, video, transcription, etc.)
            original_model: Original model identifier
            
        Returns:
            Identifier of an available alternative model or None if none is available
        """
        if model_type not in self.configs:
            logger.warning(f"No failover configuration for model type: {model_type}")
            return None
        
        config = self.configs[model_type]
        
        # Check if the original model has alternatives
        if original_model not in config.alternatives:
            logger.warning(f"No alternatives configured for model: {original_model}")
            return None
        
        # Get the list of alternatives
        alternatives = config.alternatives[original_model]
        if not alternatives:
            return None
        
        # Filter available alternatives
        available_alternatives = [
            alt for alt in alternatives 
            if alt in self.model_status and self.model_status[alt].should_retry(config.cooldown_period)
        ]
        
        if not available_alternatives:
            logger.warning(f"No available alternatives for {original_model}")
            return None
        
        # Choose an alternative randomly (simple load balancing)
        return random.choice(available_alternatives)
    
    def mark_model_failure(self, model_id: str) -> None:
        """Marks a model as having failed."""
        self._ensure_model_status(model_id)
        self.model_status[model_id].mark_failure()
        logger.warning(f"Model marked as failed: {model_id}")
    
    def mark_model_success(self, model_id: str) -> None:
        """Marks a model as functional."""
        self._ensure_model_status(model_id)
        
        # If the model was previously failing, increment the recovery counter
        if not self.model_status[model_id].available:
            self.metrics["models_recovered"] += 1
            logger.info(f"Model recovered: {model_id}")
        
        self.model_status[model_id].mark_success()
    
    def record_failover(self, original_model: str, alternative_model: str, success: bool, error: Optional[str] = None) -> None:
        """Records a failover event for analysis."""
        event = {
            "timestamp": time.time(),
            "original_model": original_model,
            "alternative_model": alternative_model,
            "success": success,
            "error": error
        }
        
        self.failover_history.append(event)
        
        # Limit the history size
        if len(self.failover_history) > self.history_max_size:
            self.failover_history.pop(0)
        
        # Update metrics
        self.metrics["total_failovers"] += 1
        if success:
            self.metrics["successful_failovers"] += 1
        else:
            self.metrics["failed_failovers"] += 1
    
    def get_model_health_report(self) -> Dict[str, Any]:
        """Generates a report on the health status of models."""
        report = {
            "metrics": self.metrics.copy(),
            "models": {}
        }
        
        for model_id, status in self.model_status.items():
            report["models"][model_id] = {
                "available": status.available,
                "failure_count": status.failure_count,
                "recovery_count": status.recovery_count,
                "last_failure": status.last_failure_time,
                "total_errors": status.cumulative_errors
            }
        
        return report

# Create a single instance of the manager
failover_manager = FailoverManager()

# Default failover configuration for different model types
default_text_failover = FailoverConfig(
    model_type="text",
    alternatives={
        "deepseek-coder-33b-instruct": ["deepseek-coder-6.7b-instruct", "codellama-7b-instruct"],
        "llama-3-70b-instruct": ["llama-3-8b-instruct", "mistral-7b-instruct"],
        "mistral-7b-instruct": ["llama-3-8b-instruct", "deepseek-coder-6.7b-instruct"],
        "claude-3-haiku": ["llama-3-8b-instruct", "mistral-7b-instruct"],
    }
)

default_transcription_failover = FailoverConfig(
    model_type="transcription",
    alternatives={
        "whisper-large-v3": ["whisper-medium", "whisper-small"],
        "whisper-medium": ["whisper-small", "whisper-base"],
        "whisper-small": ["whisper-base", "whisper-tiny"],
    }
)

default_video_failover = FailoverConfig(
    model_type="video",
    alternatives={
        "internvideo-14b": ["internvideo-7b", "videollama-7b"],
        "videollama-7b": ["internvideo-7b", "videollama-3b"],
    }
)

# Register default configurations
failover_manager.register_config(default_text_failover)
failover_manager.register_config(default_transcription_failover)
failover_manager.register_config(default_video_failover)

class FailoverMiddleware(BaseHTTPMiddleware):
    """
    Middleware that manages automatic failover between models in case of errors.
    Improves system resilience in the face of specific model problems.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: List[str] = None,
        exclude_prefixes: List[str] = None,
        default_model_type: str = "text",
    ):
        """
        Initializes the failover middleware.
        
        Args:
            app: ASGI Application
            exclude_paths: Paths excluded from failover processing
            exclude_prefixes: Path prefixes excluded from failover processing
            default_model_type: Default model type when not specified
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/api/health", "/api/docs", "/api/redoc", "/api/openapi.json"]
        self.exclude_prefixes = exclude_prefixes or ["/static/", "/docs/"]
        self.default_model_type = default_model_type
        
        # Model type indicators in URLs
        self.model_type_indicators = {
            "/transcription/": "transcription",
            "/video/": "video",
            "/inference/": "text",
            "/inference/text": "text",
            "/inference/embedding": "embedding",
            "/inference/image": "image",
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Processes requests with failover strategy."""
        # Check if this path should be excluded
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # Get the model type and original model identifier
        model_type, model_id = self._extract_model_info(request)
        
        # If no model is specified, no failover is possible
        if not model_id:
            return await call_next(request)
        
        # Try to execute the original request
        try:
            response = await call_next(request)
            
            # If the response is successful, mark the model as functional
            if response.status_code < 400:
                failover_manager.mark_model_success(model_id)
                return response
            
            # If it's an application-specific error, don't failover
            if response.status_code in [400, 401, 403, 404]:
                return response
            
        except Exception as e:
            logger.error(f"Exception during original request: {str(e)}")
            failover_manager.mark_model_failure(model_id)
            # Continue to failover
        
        # If we get here, the original request failed
        failover_manager.mark_model_failure(model_id)
        
        # Try failover with an alternative model
        alternative_model = failover_manager.get_alternative_model(model_type, model_id)
        if not alternative_model:
            logger.warning(f"No alternative model available for {model_id} of type {model_type}")
            
            # Return an error indicating model failure
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "The requested model is temporarily unavailable and no alternative is available",
                    "model": model_id,
                    "type": model_type,
                    "retry_after": 300  # Suggest a delay of 5 minutes
                }
            )
        
        logger.info(f"Attempting failover from {model_id} to {alternative_model}")
        
        # Create a new request with the alternative model
        try:
            # Create a modified copy of the request
            modified_request = await self._create_modified_request(request, model_id, alternative_model)
            
            # Execute the modified request
            response = await call_next(modified_request)
            
            # Check if the alternative request succeeded
            if response.status_code < 400:
                # Record successful failover
                failover_manager.record_failover(model_id, alternative_model, True)
                failover_manager.mark_model_success(alternative_model)
                
                # Add a header to inform the client of the failover
                response.headers["X-Model-Failover"] = f"Original: {model_id}, Alternative: {alternative_model}"
                
                return response
            else:
                # Record failover failure
                failover_manager.mark_model_failure(alternative_model)
                failover_manager.record_failover(model_id, alternative_model, False, 
                                              f"Status code: {response.status_code}")
                
                # Return a detailed error
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "All available models have failed",
                        "original_model": model_id,
                        "alternative_model": alternative_model,
                        "retry_after": 600  # Suggest a longer delay
                    }
                )
        
        except Exception as e:
            logger.error(f"Exception during failover: {str(e)}")
            failover_manager.mark_model_failure(alternative_model)
            failover_manager.record_failover(model_id, alternative_model, False, str(e))
            
            # Return an error
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Error during failover processing",
                    "message": str(e),
                    "original_model": model_id,
                    "alternative_model": alternative_model
                }
            )
    
    def _is_excluded_path(self, path: str) -> bool:
        """Checks if the path is excluded from failover processing."""
        if path in self.exclude_paths:
            return True
        
        for prefix in self.exclude_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _extract_model_info(self, request: Request) -> Tuple[str, Optional[str]]:
        """
        Extracts the model type and model identifier from the request.
        
        Args:
            request: FastAPI Request
            
        Returns:
            Tuple containing the model type and model identifier
        """
        # Determine the model type from the path
        model_type = self.default_model_type
        for indicator, type_value in self.model_type_indicators.items():
            if indicator in request.url.path:
                model_type = type_value
                break
        
        # Get the model identifier
        model_id = request.query_params.get("model")
        
        # If the model is not in the query params, look in the body
        if not model_id and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = getattr(request, "_body", None)
                if body_bytes:
                    body = json.loads(body_bytes.decode("utf-8"))
                    model_id = body.get("model") or body.get("model_id") or body.get("engine_id")
            except Exception:
                pass
        
        return model_type, model_id
    
    async def _create_modified_request(self, request: Request, original_model: str, alternative_model: str) -> Request:
        """
        Creates a modified copy of the request with the alternative model.
        
        Args:
            request: Original request
            original_model: Original model identifier
            alternative_model: Alternative model identifier
            
        Returns:
            Modified request
        """
        # Creating a copy of the request is complex as Request is an immutable object
        # We will instead store the alternative model in the request state
        
        request.state.alternative_model = alternative_model
        request.state.original_model = original_model
        
        # For requests with a body, we need to replace the model in the body
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = getattr(request, "_body", None)
                if body_bytes:
                    body = json.loads(body_bytes.decode("utf-8"))
                    
                    # Replace the model in the body
                    if "model" in body:
                        body["model"] = alternative_model
                    elif "model_id" in body:
                        body["model_id"] = alternative_model
                    elif "engine_id" in body:
                        body["engine_id"] = alternative_model
                    
                    # Replace the request body
                    new_body = json.dumps(body).encode("utf-8")
                    request._body = new_body
            except Exception as e:
                logger.error(f"Error when modifying the body: {str(e)}")
        
        return request

# Function to get model health
def get_models_health() -> Dict[str, Any]:
    """Gets a report on the health status of models."""
    return failover_manager.get_model_health_report()

# Function to reset a model manually
def reset_model_status(model_id: str) -> Dict[str, Any]:
    """Manually resets a model's status."""
    if model_id in failover_manager.model_status:
        failover_manager.mark_model_success(model_id)
        return {"success": True, "message": f"Model status {model_id} reset"}
    else:
        return {"success": False, "message": f"Model {model_id} not found"}

# Function to configure alternatives for a model
def configure_failover(
    model_type: str,
    model_id: str,
    alternatives: List[str],
    max_retries: int = 3,
    cooldown_period: int = 300
) -> Dict[str, Any]:
    """
    Configures failover alternatives for a model.
    
    Args:
        model_type: Model type
        model_id: Model identifier
        alternatives: List of alternative model identifiers
        max_retries: Maximum number of retry attempts
        cooldown_period: Cooling period in seconds
        
    Returns:
        Result dictionary
    """
    # Check if a configuration already exists for this type
    if model_type not in failover_manager.configs:
        config = FailoverConfig(
            model_type=model_type,
            alternatives={model_id: alternatives},
            max_retries=max_retries,
            cooldown_period=cooldown_period
        )
        failover_manager.register_config(config)
    else:
        # Update the existing configuration
        failover_manager.configs[model_type].alternatives[model_id] = alternatives
        failover_manager.configs[model_type].max_retries = max_retries
        failover_manager.configs[model_type].cooldown_period = cooldown_period
    
    return {
        "success": True,
        "message": f"Failover configuration updated for {model_id} of type {model_type}"
    }