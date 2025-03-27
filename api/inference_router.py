"""
Router for AI model inferences
------------------------------------------
This module implements routes for running inferences with different AI models.
"""
# For access to post-processor configurations
from config import postprocessing_config

# For accessing the request and using the post-processor
from fastapi import Request
import os
import time
import logging
import uuid
import json
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, File, UploadFile, Form, Body
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field, validator

# Import response models
from .response_models import (
    SuccessResponse, 
    ErrorResponse, 
    TaskResponse, 
    TaskStatusResponse,
    TaskListResponse
)

# Import authentication utilities
from auth import get_current_active_user, User

# Import model manager
from model_manager import ModelManager

# Import prompt manager
from utils.prompt_manager import get_prompt_manager

# Import inference engine
from inference_engine import (
    run_inference,
    get_task_status,
    list_tasks,
    cancel_task,
    get_available_models,
    ModelNotFoundException
)

# Logging configuration
logger = logging.getLogger("api.inference")

# Create directories for results
RESULTS_DIR = Path("inference_results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Create router
inference_router = APIRouter(
    prefix="/inference",
    tags=["Inference"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Resource not found"},
        500: {"model": ErrorResponse, "description": "Server error"}
    }
)

# Pydantic models for requests
class TextInferenceRequest(BaseModel):
    """Model for text inference requests"""
    model: str
    text: Optional[str] = None
    prompt: Optional[str] = None
    prompt_name: Optional[str] = None
    language: Optional[str] = "fr"
    context: Optional[str] = None
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    
    @validator('prompt_name')
    def validate_prompt_name(cls, v, values):
        """Verifies that either a custom prompt, a prompt name, or text is specified"""
        if not v and not values.get('prompt') and not values.get('text'):
            raise ValueError("You must specify either 'prompt_name', 'prompt', or 'text'")
        return v

class TextCompletionResponse(BaseModel):
    """Model for text completion responses"""
    id: str = Field(..., description="Unique task identifier")
    text: str = Field(..., description="Generated text")
    model: str = Field(..., description="Model used")
    usage: Dict[str, int] = Field(..., description="Usage statistics")

class ImageGenerationRequest(BaseModel):
    """Model for image generation requests"""
    model: str
    prompt: str
    prompt_name: Optional[str] = None
    text: Optional[str] = None
    n: Optional[int] = 1
    size: Optional[str] = "1024x1024"
    response_format: Optional[str] = "url"
    
    @validator('prompt')
    def validate_prompt(cls, v, values):
        """Verifies that either a custom prompt, or a prompt name with text is specified"""
        if not v and not values.get('prompt_name') and not values.get('text'):
            raise ValueError("You must specify either 'prompt', or 'prompt_name' with 'text'")
        return v

class ImageGenerationResponse(BaseModel):
    """Model for image generation responses"""
    id: str = Field(..., description="Unique task identifier")
    images: List[str] = Field(..., description="URLs of generated images")
    model: str = Field(..., description="Model used")

class ModelsResponse(BaseModel):
    """Model for the list of available models"""
    text_models: Dict[str, Any] = Field(..., description="Available text models")
    image_models: Dict[str, Any] = Field(..., description="Available image models")
    embedding_models: Dict[str, Any] = Field(..., description="Available embedding models")

class PostProcessingOptions(BaseModel):
    """Post-processing options for inferences"""
    json_simplify: Optional[bool] = False

# Inference routes
@inference_router.post("/text", response_model=TaskResponse)
async def create_text_inference(
    request: TextInferenceRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """Creates an inference task for text generation"""
    try:
        task_id = str(uuid.uuid4())
        prompt_manager = get_prompt_manager()
        final_prompt = None
        
        # Prompt management with the PromptManager
        if request.prompt_name:
            # Use a predefined prompt with the provided text
            placeholder_values = {}
            if request.text:
                placeholder_values["text"] = request.text
            if request.language:
                placeholder_values["language"] = request.language
            if request.context:
                placeholder_values["context"] = request.context
                
            final_prompt = prompt_manager.format_prompt(
                request.prompt_name, 
                **placeholder_values
            )
            
            if not final_prompt:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unable to format prompt '{request.prompt_name}'. Check required placeholders."
                )
        elif request.prompt:
            # Use the provided prompt directly
            final_prompt = request.prompt
        elif request.text:
            # Use the default prompt with the provided text
            final_prompt = prompt_manager.format_prompt("default", text=request.text)
            if not final_prompt:
                # Fallback if default prompt doesn't exist
                final_prompt = f"Analyze the following text:\n\n{request.text}"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must provide either 'prompt_name', 'prompt', or 'text'."
            )
        
        # Inference parameters
        params = {
            "model": request.model,
            "prompt": final_prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "n": request.n,
            "stop": request.stop,
            "presence_penalty": request.presence_penalty,
            "frequency_penalty": request.frequency_penalty,
            "user_id": current_user.username
        }
        
        # Launch task in background
        background_tasks.add_task(
            run_inference,
            task_id=task_id,
            task_type="text",
            params=params
        )
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message="Inference task created"
        )
    
    except ModelNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model not found: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating inference task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating task: {str(e)}"
        )

@inference_router.post("/image", response_model=TaskResponse)
async def create_image_generation(
    request: ImageGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """Creates an inference task for image generation"""
    try:
        task_id = str(uuid.uuid4())
        prompt_manager = get_prompt_manager()
        final_prompt = None
        
        # Prompt management with the PromptManager
        if request.prompt_name and request.text:
            # Use a predefined prompt with the provided text
            final_prompt = prompt_manager.format_prompt(request.prompt_name, text=request.text)
            if not final_prompt:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unable to format prompt '{request.prompt_name}'. Check required placeholders."
                )
        elif request.prompt:
            # Use the provided prompt directly
            final_prompt = request.prompt
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must provide either 'prompt', or 'prompt_name' with 'text'."
            )
        
        # Inference parameters
        params = {
            "model": request.model,
            "prompt": final_prompt,
            "n": request.n,
            "size": request.size,
            "response_format": request.response_format,
            "user_id": current_user.username
        }
        
        # Launch task in background
        background_tasks.add_task(
            run_inference,
            task_id=task_id,
            task_type="image",
            params=params
        )
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message="Image generation task created"
        )
    
    except ModelNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model not found: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating image generation task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating task: {str(e)}"
        )

@inference_router.post("/embedding", response_model=TaskResponse)
async def create_embedding(
    text: str = Body(..., embed=True),
    model: str = Body(..., embed=True),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_active_user)
):
    """Creates an inference task for embedding generation"""
    try:
        task_id = str(uuid.uuid4())
        
        # Inference parameters
        params = {
            "model": model,
            "text": text,
            "user_id": current_user.username
        }
        
        # Launch task in background
        background_tasks.add_task(
            run_inference,
            task_id=task_id,
            task_type="embedding",
            params=params
        )
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message="Embedding generation task created"
        )
    
    except ModelNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating embedding task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating task: {str(e)}"
        )

@inference_router.post("/chain", response_model=TaskResponse)
async def create_inference_chain(
    text: str = Body(...),
    prompt_sequence: List[str] = Body(...),
    model: str = Body(...),
    max_tokens: Optional[int] = Body(1024),
    temperature: Optional[float] = Body(0.7),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_active_user)
):
    """Creates a chain inference task (sequence of prompts)"""
    try:
        task_id = str(uuid.uuid4())
        prompt_manager = get_prompt_manager()
        
        # Verify that all prompts in the sequence exist
        for prompt_name in prompt_sequence:
            if not prompt_manager.get_prompt(prompt_name):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Prompt '{prompt_name}' does not exist in the sequence"
                )
        
        # Inference parameters
        params = {
            "model": model,
            "text": text,
            "prompt_sequence": prompt_sequence,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "user_id": current_user.username
        }
        
        # Launch task in background
        background_tasks.add_task(
            run_inference,
            task_id=task_id,
            task_type="chain",
            params=params
        )
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message="Chain inference task created"
        )
    
    except ModelNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model not found: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating chain inference task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating task: {str(e)}"
        )

@inference_router.post("/custom", response_model=TaskResponse)
async def create_custom_inference(
    text: str = Body(...),
    prompt_name: str = Body(...),
    model: str = Body(...),
    max_tokens: Optional[int] = Body(1024),
    temperature: Optional[float] = Body(0.7),
    language: Optional[str] = Body("fr"),
    context: Optional[str] = Body(None),
    content: Optional[str] = Body(None),
    additional_context: Optional[Dict[str, Any]] = Body(None),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_active_user)
):
    """Creates an inference task with custom placeholders"""
    try:
        task_id = str(uuid.uuid4())
        prompt_manager = get_prompt_manager()
        
        # Verify that the prompt exists
        if not prompt_manager.get_prompt(prompt_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Prompt '{prompt_name}' does not exist"
            )
        
        # Prepare placeholders
        placeholder_values = {
            "text": text,
            "language": language
        }
        
        # Add optional placeholders if present
        if context:
            placeholder_values["context"] = context
        if content:
            placeholder_values["content"] = content
            
        # Add any additional context as placeholders
        if additional_context:
            placeholder_values.update(additional_context)
        
        # Format the prompt
        final_prompt = prompt_manager.format_prompt(prompt_name, **placeholder_values)
        
        if not final_prompt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to format prompt '{prompt_name}'. Check required placeholders."
            )
        
        # Inference parameters
        params = {
            "model": model,
            "prompt": final_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "user_id": current_user.username
        }
        
        # Launch task in background
        background_tasks.add_task(
            run_inference,
            task_id=task_id,
            task_type="text",
            params=params
        )
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message="Custom inference task created"
        )
    
    except ModelNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model not found: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating custom inference task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating task: {str(e)}"
        )

@inference_router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves the status of an inference task"""
    try:
        task = get_task_status(task_id)
        
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
            
        # Check if the user is authorized to access this task
        if not current_user.is_admin and task.get("user_id") != current_user.username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this task"
            )
            
        return TaskStatusResponse(**task)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving task: {str(e)}"
        )

@inference_router.get("/tasks", response_model=TaskListResponse)
async def get_tasks(
    current_user: User = Depends(get_current_active_user),
    limit: int = 10,
    offset: int = 0
):
    """Retrieves the list of inference tasks"""
    try:
        # Filter tasks by user (except for admins)
        user_filter = None if current_user.is_admin else current_user.username
        
        tasks = list_tasks(limit=limit, offset=offset, user_id=user_filter)
        
        return TaskListResponse(
            total=tasks.get("total", 0),
            tasks=tasks.get("tasks", {})
        )
        
    except Exception as e:
        logger.error(f"Error retrieving tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tasks: {str(e)}"
        )

@inference_router.delete("/task/{task_id}", response_model=SuccessResponse)
async def cancel_task_endpoint(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Cancels an inference task"""
    try:
        # Check if the task exists and belongs to the user
        task = get_task_status(task_id)
        
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
            
        # Check if the user is authorized to cancel this task
        if not current_user.is_admin and task.get("user_id") != current_user.username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to cancel this task"
            )
            
        # Cancel the task
        result = cancel_task(task_id)
        
        if not result:
            return SuccessResponse(
                success=False,
                message="The task cannot be canceled because it has already completed"
            )
            
        return SuccessResponse(
            success=True,
            message=f"Task {task_id} successfully canceled"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error canceling task: {str(e)}"
        )

@inference_router.get("/models", response_model=ModelsResponse)
async def get_models():
    """Retrieves the list of available inference models"""
    try:
        models = get_available_models()
        
        return ModelsResponse(
            text_models=models.get("text", {}),
            image_models=models.get("image", {}),
            embedding_models=models.get("embedding", {})
        )
        
    except Exception as e:
        logger.error(f"Error retrieving models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving models: {str(e)}"
        )

@inference_router.get("/prompts")
async def get_available_prompts(
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves the list of available prompts"""
    try:
        prompt_manager = get_prompt_manager()
        available_prompts = prompt_manager.list_prompts()
        
        prompts_with_placeholders = {}
        for prompt_name in available_prompts:
            prompts_with_placeholders[prompt_name] = {
                "placeholders": prompt_manager.get_placeholder_names(prompt_name)
            }
        
        return {
            "prompts": prompts_with_placeholders
        }
        
    except Exception as e:
        logger.error(f"Error retrieving prompts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving prompts: {str(e)}"
        )

@inference_router.get("/results/{task_id}")
async def get_results(
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves the results of an inference task"""
    try:
        # Check if the task exists and belongs to the user
        task = get_task_status(task_id)
        
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
            
        # Check if the user is authorized to access this task
        if not current_user.is_admin and task.get("user_id") != current_user.username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access these results"
            )
            
        # Check if the task is completed
        if task.get("status") != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Task {task_id} is not yet completed"
            )
            
        # Check the result type
        task_type = task.get("task_type")
        results = task.get("results")
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No results available for task {task_id}"
            )
        
        # Prepare the response based on the task type
        if task_type == "image":
            # For images, return URLs or files
            if results.get("format") == "url":
                response_data = {"images": results.get("images", [])}
            else:
                # TODO: Handle image files
                response_data = results
                
        elif task_type == "text":
            # For text, simply return the result
            response_data = {"text": results.get("text", ""), "usage": results.get("usage", {})}
            
        elif task_type == "embedding":
            # For embeddings, return the vectors
            response_data = {"embedding": results.get("embedding", [])}
            
        elif task_type == "chain":
            # For inference chains, return intermediate results
            response_data = {
                "final_result": results.get("final_result", ""),
                "intermediate_results": results.get("intermediate_results", {})
            }
            
        else:
            # By default, return all results
            response_data = results
        
        # Apply JSONSimplifier post-processor if available and enabled
        json_simplifier = getattr(request.app.state, "json_simplifier", None)
        if json_simplifier and json_simplifier.should_process("inference"):
            logger.debug(f"Applying JSONSimplifier post-processor to results of task {task_id}")
            response_data = json_simplifier.process(response_data, "inference")
            
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving results: {str(e)}"
        )

@inference_router.post("/text/with-options", response_model=TaskResponse)
async def create_text_inference_with_options(
    request: TextInferenceRequest,
    options: PostProcessingOptions = Body(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_active_user)
):
    """Creates a text generation inference task with post-processing options"""
    try:
        task_id = str(uuid.uuid4())
        prompt_manager = get_prompt_manager()
        final_prompt = None
        
        # Prompt management with the PromptManager
        if request.prompt_name:
            # Use a predefined prompt with the provided text
            placeholder_values = {}
            if request.text:
                placeholder_values["text"] = request.text
            if request.language:
                placeholder_values["language"] = request.language
            if request.context:
                placeholder_values["context"] = request.context
                
            final_prompt = prompt_manager.format_prompt(
                request.prompt_name, 
                **placeholder_values
            )
            
            if not final_prompt:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unable to format prompt '{request.prompt_name}'. Check required placeholders."
                )
        elif request.prompt:
            # Use the provided prompt directly
            final_prompt = request.prompt
        elif request.text:
            # Use the default prompt with the provided text
            final_prompt = prompt_manager.format_prompt("default", text=request.text)
            if not final_prompt:
                # Fallback if default prompt doesn't exist
                final_prompt = f"Analyze the following text:\n\n{request.text}"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must provide either 'prompt_name', 'prompt', or 'text'."
            )
        
        # Inference parameters
        params = {
            "model": request.model,
            "prompt": final_prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "n": request.n,
            "stop": request.stop,
            "presence_penalty": request.presence_penalty,
            "frequency_penalty": request.frequency_penalty,
            "user_id": current_user.username,
            # Add post-processing options
            "post_processing": {
                "json_simplify": options.json_simplify
            }
        }
        
        # Launch task in background
        background_tasks.add_task(
            run_inference,
            task_id=task_id,
            task_type="text",
            params=params
        )
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message="Inference task created with post-processing options"
        )
    
    except ModelNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model not found: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating inference task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating task: {str(e)}"
        )

@inference_router.get("/postprocessors")
async def get_postprocessors_config(
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves the configuration of active post-processors"""
    try:
        # Get active post-processor configuration
        json_simplifier_config = postprocessing_config.get("json_simplifier", {})
        
        return {
            "json_simplifier": {
                "enabled": json_simplifier_config.get("enabled", False),
                "model": json_simplifier_config.get("model"),
                "apply_to": json_simplifier_config.get("apply_to", [])
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving post-processors configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving configuration: {str(e)}"
        )