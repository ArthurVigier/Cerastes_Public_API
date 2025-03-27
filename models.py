from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import time

class InferenceRequest(BaseModel):
    """Model for inference requests."""
    text: str = Field(..., description="Text to analyze")
    use_segmentation: bool = Field(True, description="Use text segmentation")
    max_new_tokens: int = Field(8000, description="Maximum number of generated tokens")
    batch_parallel: bool = Field(True, description="Run tasks in parallel")
    timeout_seconds: int = Field(300, description="Timeout in seconds")
    engine_id: Optional[str] = Field(None, description="ID of the inference engine to use")
    
    @validator('text')
    def text_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v
    
    @validator('max_new_tokens')
    def max_tokens_in_range(cls, v):
        if v < 100 or v > 24000:
            raise ValueError("Number of tokens must be between 100 and 24000")
        return v
    
    @validator('timeout_seconds')
    def timeout_in_range(cls, v):
        if v < 10 or v > 3600:
            raise ValueError("Timeout must be between 10 and 3600 seconds")
        return v

class InferenceResponse(BaseModel):
    """Model for inference request responses."""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task status (pending, running, completed, failed)")
    message: str = Field(..., description="Descriptive message")
    created_at: Optional[float] = Field(None, description="Creation timestamp")

class SessionRequest(BaseModel):
    """Model for specific session requests."""
    system_prompt: str = Field(..., description="System prompt to use")
    user_input: Optional[str] = Field("", description="User input to provide")
    max_new_tokens: int = Field(8000, description="Maximum number of generated tokens")
    timeout_seconds: int = Field(300, description="Timeout in seconds")
    engine_id: Optional[str] = Field(None, description="ID of the inference engine to use")
    
    @validator('system_prompt')
    def prompt_not_empty(cls, v):
        if not v.strip():
            raise ValueError("System prompt cannot be empty")
        return v
    
    @validator('max_new_tokens')
    def max_tokens_in_range(cls, v):
        if v < 100 or v > 24000:
            raise ValueError("Number of tokens must be between 100 and 24000")
        return v
    
    @validator('timeout_seconds')
    def timeout_in_range(cls, v):
        if v < 10 or v > 3600:
            raise ValueError("Timeout must be between 10 and 3600 seconds")
        return v

class SessionResponse(BaseModel):
    """Model for specific session request responses."""
    task_id: str = Field(..., description="Session task identifier")
    parent_task_id: str = Field(..., description="Parent task identifier")
    session_name: str = Field(..., description="Session name")
    status: str = Field(..., description="Task status (pending, running, completed, failed)")
    message: str = Field(..., description="Descriptive message")

class InferenceStatus(BaseModel):
    """Model for inference task statuses."""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task status (pending, running, completed, failed)")
    message: str = Field(..., description="Descriptive message")
    progress: float = Field(0, description="Progress percentage (0-100)")
    created_at: float = Field(..., description="Creation timestamp")
    started_at: Optional[float] = Field(None, description="Execution start timestamp")
    completed_at: Optional[float] = Field(None, description="Execution end timestamp")
    results: Optional[Dict[str, Any]] = Field(None, description="Inference results")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Inference metrics")
    result_file: Optional[str] = Field(None, description="Path to results file")
    error: Optional[str] = Field(None, description="Error message in case of failure")
    error_type: Optional[str] = Field(None, description="Error type in case of failure")
    
    def formatted_timestamps(self) -> Dict[str, str]:
        """Returns formatted timestamps."""
        timestamps = {}
        if self.created_at:
            timestamps["created_at"] = datetime.fromtimestamp(self.created_at).isoformat()
        if self.started_at:
            timestamps["started_at"] = datetime.fromtimestamp(self.started_at).isoformat()
        if self.completed_at:
            timestamps["completed_at"] = datetime.fromtimestamp(self.completed_at).isoformat()
        return timestamps

class BatchInferenceRequest(BaseModel):
    """Model for batch inference requests."""
    texts: List[str] = Field(..., description="List of texts to analyze")
    use_segmentation: bool = Field(True, description="Use text segmentation")
    max_new_tokens: int = Field(8000, description="Maximum number of generated tokens")
    batch_parallel: bool = Field(True, description="Run tasks in parallel")
    timeout_seconds: int = Field(300, description="Timeout in seconds")
    engine_id: Optional[str] = Field(None, description="ID of the inference engine to use")
    max_concurrent: int = Field(3, description="Maximum number of concurrent tasks")
    
    @validator('texts')
    def texts_not_empty(cls, v):
        if not v:
            raise ValueError("The list of texts cannot be empty")
        for i, text in enumerate(v):
            if not text.strip():
                raise ValueError(f"Text at index {i} cannot be empty")
        return v
    
    @validator('max_new_tokens')
    def max_tokens_in_range(cls, v):
        if v < 100 or v > 24000:
            raise ValueError("Number of tokens must be between 100 and 24000")
        return v
    
    @validator('timeout_seconds')
    def timeout_in_range(cls, v):
        if v < 10 or v > 3600:
            raise ValueError("Timeout must be between 10 and 3600 seconds")
        return v
    
    @validator('max_concurrent')
    def concurrent_in_range(cls, v):
        if v < 1 or v > 10:
            raise ValueError("Number of concurrent tasks must be between 1 and 10")
        return v

class BatchInferenceResponse(BaseModel):
    """Model for batch inference request responses."""
    batch_id: str = Field(..., description="Batch identifier")
    status: str = Field(..., description="Task status (pending, running, completed, failed)")
    message: str = Field(..., description="Descriptive message")
    batch_size: int = Field(..., description="Number of texts in the batch")