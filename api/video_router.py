"""
Router for video analysis features
----------------------------------------------
This module implements routes for extracting and analyzing video content,
including nonverbal analysis and manipulation strategies.
"""

import os
import logging
import time
import traceback
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Body, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import response models
from .response_models import (
    VideoExtractionResponse, 
    NonverbalAnalysisResponse,
    ErrorResponse,
    TaskResponse
)

# Import video processing functions
from video_models import (
    extract_video_content,
    extract_nonverbal,
    analyze_nonverbal,
    analyze_manipulation_strategies
)

# Import for authentication
from auth import get_current_active_user, User

# Import configuration
from config import video_config, system_prompts

# Import task manager
from inference_engine import (
    TaskType, 
    create_task, 
    update_task, 
    get_task_status,
    ProgressTracker
)

# Import prompt manager
from utils.prompt_manager import get_prompt_manager

# Logging configuration
logger = logging.getLogger("api.video")

# Create router
video_router = APIRouter(
    prefix="/video",
    tags=["Video"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "File not found"},
        500: {"model": ErrorResponse, "description": "Server error"}
    }
)

# Configuration
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results/videos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Pydantic models for requests
class AnalysisRequest(BaseModel):
    extraction_text: str
    extraction_path: Optional[str] = None

def allowed_file(filename: str) -> bool:
    """Checks if the file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

async def save_uploaded_file(file: UploadFile) -> str:
    """Saves an uploaded file and returns its path"""
    if not file:
        raise HTTPException(status_code=400, detail="No file was provided")
    
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    # Secure filename
    filename = "".join(c for c in file.filename if c.isalnum() or c in "._- ")
    timestamp = int(time.time())
    safe_path = os.path.join(UPLOAD_FOLDER, f"{timestamp}_{filename}")
    
    # Save file
    contents = await file.read()
    with open(safe_path, "wb") as f:
        f.write(contents)
    
    return safe_path

def create_output_filename(original_filename: str, prefix: str = "video") -> str:
    """Creates a filename for the video analysis output"""
    base_name = os.path.basename(original_filename)
    name_without_ext = os.path.splitext(base_name)[0]
    timestamp = int(time.time())
    return os.path.join(RESULTS_FOLDER, f"{prefix}_{name_without_ext}_{timestamp}.txt")

def progress_callback(progress: float, desc: str) -> None:
    """Progress function (for compatibility)"""
    logger.debug(f"Progress: {progress*100:.1f}% - {desc}")

# Analysis function with prompt manager
def formatted_analyze_nonverbal(extraction_text: str, extraction_path: Optional[str], progress=None):
    """Modified version of analyze_nonverbal using the prompt manager"""
    prompt_manager = get_prompt_manager()
    
    # Use formatted prompt with placeholder {text}
    if "nonverbal_analysis" in system_prompts:
        prompt = prompt_manager.format_prompt_direct(
            system_prompts["nonverbal_analysis"], 
            text=extraction_text
        )
    else:
        # Fallback to default prompt if not found
        prompt = prompt_manager.format_prompt_direct(
            "Analyze the nonverbal cues in the following video content: {text}",
            text=extraction_text
        )
    
    # Call the original function with the formatted prompt
    return analyze_nonverbal(prompt, extraction_path, progress=progress)

# Analysis function with prompt manager
def formatted_analyze_manipulation(extraction_text: str, extraction_path: Optional[str], progress=None):
    """Modified version of analyze_manipulation_strategies using the prompt manager"""
    prompt_manager = get_prompt_manager()
    
    # Use formatted prompt with placeholder {text}
    if "manipulation_analysis" in system_prompts:
        prompt = prompt_manager.format_prompt_direct(
            system_prompts["manipulation_analysis"], 
            text=extraction_text
        )
    else:
        # Fallback to default prompt if not found
        prompt = prompt_manager.format_prompt_direct(
            "Analyze the manipulation strategies in the following video content: {text}",
            text=extraction_text
        )
    
    # Call the original function with the formatted prompt
    return analyze_manipulation_strategies(prompt, extraction_path, progress=progress)

async def process_video_task(task_id: str, task_type: str, video_path: str, **kwargs):
    """Asynchronous function to process a video task in the background"""
    try:
        # Update status
        update_task(task_id, {
            "status": "running",
            "message": "Video processing in progress..."
        })
        
        # Initialize progress tracker
        progress_tracker = ProgressTracker(task_id)
        
        # Determine task type and function to call
        if task_type == TaskType.VIDEO_NONVERBAL:
            update_task(task_id, {"message": "Extracting nonverbal cues..."})
            content, temp_path = extract_nonverbal(video_path, progress=progress_tracker)
            result = {
                "content": content,
                "file_path": temp_path
            }
            success_message = "Nonverbal cues extraction completed successfully"
        
        elif task_type == TaskType.VIDEO_MANIPULATION:
            update_task(task_id, {"message": "Extracting video content..."})
            content, temp_path = extract_video_content(video_path, progress=progress_tracker)
            result = {
                "content": content,
                "file_path": temp_path
            }
            success_message = "Video content extraction completed successfully"
        
        else:
            raise ValueError(f"Unsupported video task type: {task_type}")
            
        # Update with results
        update_task(task_id, {
            "status": "completed",
            "results": result,
            "message": success_message
        })
        
        logger.info(f"Video task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error during video task {task_id}: {str(e)}")
        logger.error(traceback.format_exc())
        update_task(task_id, {
            "status": "failed",
            "error": str(e),
            "message": f"Error: {str(e)}"
        })

@video_router.post('/extract', response_model=VideoExtractionResponse)
async def video_extraction(
    video: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Extracts content from a video"""
    try:
        # Save uploaded video
        video_path = await save_uploaded_file(video)
        logger.info(f"Video saved to {video_path}")
        
        # Extract video content
        content, temp_path = extract_video_content(
            video_path, 
            progress=lambda progress, desc: logger.debug(f"Progress: {progress*100:.1f}% - {desc}")
        )
        
        # Prepare response
        response = VideoExtractionResponse(
            content=content,
            file_path=temp_path,
            message="Video extraction successful"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during video extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during video extraction: {str(e)}")

@video_router.post('/extract_nonverbal', response_model=VideoExtractionResponse)
async def nonverbal_extraction(
    video: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Extracts nonverbal cues from a video"""
    try:
        # Save uploaded video
        video_path = await save_uploaded_file(video)
        logger.info(f"Video saved to {video_path}")
        
        # Extract nonverbal cues
        content, temp_path = extract_nonverbal(
            video_path, 
            progress=lambda progress, desc: logger.debug(f"Progress: {progress*100:.1f}% - {desc}")
        )
        
        # Prepare response
        response = VideoExtractionResponse(
            content=content,
            file_path=temp_path,
            message="Nonverbal cues extraction successful"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during nonverbal cues extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during nonverbal cues extraction: {str(e)}")

@video_router.post('/analyze_nonverbal', response_model=NonverbalAnalysisResponse)
async def analyze_nonverbal_api(
    request: Request,
    analysis_req: AnalysisRequest = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """Analyzes nonverbal cues in a video"""
    try:
        # Analyze nonverbal cues with prompt manager
        analysis = formatted_analyze_nonverbal(
            analysis_req.extraction_text, 
            analysis_req.extraction_path, 
            progress=progress_callback
        )
        
        # Apply JSONSimplifier post-processor if available
        result = {"analysis": analysis, "message": "Nonverbal cues analysis successful"}
        json_simplifier = getattr(request.app.state, "json_simplifier", None)
        if json_simplifier and json_simplifier.should_process("video"):
            result = json_simplifier.process(result, "video")
        
        # Prepare response
        response = NonverbalAnalysisResponse(**result)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during nonverbal cues analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during nonverbal cues analysis: {str(e)}")

@video_router.post('/analyze_manipulation', response_model=NonverbalAnalysisResponse)
async def analyze_manipulation_api(
    request: Request,
    analysis_req: AnalysisRequest = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """Analyzes manipulation strategies in a video"""
    try:
        # Analyze manipulation strategies with prompt manager
        analysis = formatted_analyze_manipulation(
            analysis_req.extraction_text, 
            analysis_req.extraction_path, 
            progress=progress_callback
        )
        
        # Apply JSONSimplifier post-processor if available
        result = {"analysis": analysis, "message": "Manipulation strategies analysis successful"}
        json_simplifier = getattr(request.app.state, "json_simplifier", None)
        if json_simplifier and json_simplifier.should_process("video"):
            result = json_simplifier.process(result, "video")
        
        # Prepare response
        response = NonverbalAnalysisResponse(**result)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during manipulation strategies analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during manipulation strategies analysis: {str(e)}")

@video_router.post('/async_extract', response_model=TaskResponse)
async def async_video_extraction(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    extract_type: str = Form("standard"),  # 'standard' or 'nonverbal'
    current_user: User = Depends(get_current_active_user)
):
    """Starts an asynchronous video extraction (in background)"""
    try:
        # Save uploaded video
        video_path = await save_uploaded_file(video)
        logger.info(f"Video saved to {video_path} for asynchronous extraction")
        
        # Determine task type
        if extract_type.lower() == "nonverbal":
            task_type = TaskType.VIDEO_NONVERBAL
            task_desc = "nonverbal cues extraction"
        else:
            task_type = TaskType.VIDEO_MANIPULATION
            task_desc = "video content extraction"
        
        # Task parameters
        task_params = {
            "video_path": video_path,
            "extract_type": extract_type,
            "output_txt": create_output_filename(video_path, prefix=extract_type)
        }
        
        # Create task
        task_id = create_task(
            task_type=task_type,
            user_id=current_user.username,
            params=task_params
        )
        
        # Launch task in background
        background_tasks.add_task(
            process_video_task,
            task_id=task_id,
            task_type=task_type,
            video_path=video_path,
            **task_params
        )
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message=f"{task_desc} task launched successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error launching asynchronous video extraction: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error launching asynchronous video extraction: {str(e)}"
        )

@video_router.post('/async_analyze', response_model=TaskResponse)
async def async_video_analysis(
    background_tasks: BackgroundTasks,
    analysis_type: str = Form(...),  # 'nonverbal' or 'manipulation'
    extraction_text: str = Form(...),
    extraction_path: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """Starts an asynchronous video analysis (in background)"""
    try:
        # Check analysis type
        if analysis_type not in ["nonverbal", "manipulation"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid analysis type. Use 'nonverbal' or 'manipulation'"
            )
        
        # Task parameters
        task_params = {
            "extraction_text": extraction_text,
            "extraction_path": extraction_path,
            "analysis_type": analysis_type
        }
        
        # Determine task type
        if analysis_type == "nonverbal":
            task_type = TaskType.VIDEO_NONVERBAL
            task_desc = "nonverbal cues analysis"
        else:
            task_type = TaskType.VIDEO_MANIPULATION
            task_desc = "manipulation strategies analysis"
        
        # Create task
        task_id = create_task(
            task_type=task_type,
            user_id=current_user.username,
            params=task_params
        )
        
        # Function to execute analysis in background
        async def execute_analysis(task_id: str, analysis_type: str, extraction_text: str, extraction_path: Optional[str]):
            try:
                # Update status
                update_task(task_id, {
                    "status": "running",
                    "message": f"{analysis_type} analysis in progress..."
                })
                
                # Initialize progress tracker
                progress_tracker = ProgressTracker(task_id)
                
                # Get prompt manager
                prompt_manager = get_prompt_manager()
                
                # Execute appropriate analysis with formatted prompts
                if analysis_type == "nonverbal":
                    # Format prompt for nonverbal analysis
                    if "nonverbal_analysis" in system_prompts:
                        formatted_text = prompt_manager.format_prompt_direct(
                            system_prompts["nonverbal_analysis"], 
                            text=extraction_text
                        )
                    else:
                        formatted_text = prompt_manager.format_prompt_direct(
                            "Analyze the nonverbal cues in the following video content: {text}",
                            text=extraction_text
                        )
                    
                    analysis = analyze_nonverbal(
                        formatted_text, 
                        extraction_path, 
                        progress=progress_tracker
                    )
                    success_message = "Nonverbal cues analysis completed successfully"
                else:
                    # Format prompt for manipulation analysis
                    if "manipulation_analysis" in system_prompts:
                        formatted_text = prompt_manager.format_prompt_direct(
                            system_prompts["manipulation_analysis"], 
                            text=extraction_text
                        )
                    else:
                        formatted_text = prompt_manager.format_prompt_direct(
                            "Analyze the manipulation strategies in the following video content: {text}",
                            text=extraction_text
                        )
                    
                    analysis = analyze_manipulation_strategies(
                        formatted_text, 
                        extraction_path, 
                        progress=progress_tracker
                    )
                    success_message = "Manipulation strategies analysis completed successfully"
                
                # Get JSONSimplifier if available
                from main import app
                json_simplifier = getattr(app.state, "json_simplifier", None)
                
                # Prepare result
                result = analysis
                
                # Apply post-processor if available
                if json_simplifier and json_simplifier.should_process("video"):
                    result_dict = {"result": result}
                    processed = json_simplifier.process(result_dict, "video")
                    result = processed.get("result", result)
                    
                    # If plain text explanation is available, add it to results
                    if "plain_explanation" in processed:
                        result["plain_explanation"] = processed["plain_explanation"]
                
                # Update with results
                update_task(task_id, {
                    "status": "completed",
                    "results": result,
                    "message": success_message
                })
                
                logger.info(f"Analysis task {task_id} completed successfully")
                
            except Exception as e:
                logger.error(f"Error during analysis task {task_id}: {str(e)}")
                logger.error(traceback.format_exc())
                update_task(task_id, {
                    "status": "failed",
                    "error": str(e),
                    "message": f"Error: {str(e)}"
                })
        
        # Launch task in background
        background_tasks.add_task(
            execute_analysis,
            task_id=task_id,
            analysis_type=analysis_type,
            extraction_text=extraction_text,
            extraction_path=extraction_path
        )
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message=f"{task_desc} task launched successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error launching asynchronous video analysis: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error launching asynchronous video analysis: {str(e)}"
        )

@video_router.get('/allowed_extensions')
async def get_allowed_extensions():
    """Retrieves the list of allowed video file extensions"""
    return {
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "max_upload_size_mb": video_config["max_upload_size_mb"]
    }

@video_router.get('/task/{task_id}/result', response_model=None)
async def get_task_result(
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves the result of a video analysis task"""
    try:
        # Get task status
        task = get_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        if task["status"] != "completed":
            return {
                "status": task["status"],
                "message": task.get("message", "Task is being processed")
            }
        
        # Get results
        result = task.get("results", {})
        
        # Apply JSONSimplifier post-processor if available and not already applied
        if "plain_explanation" not in result:
            json_simplifier = getattr(request.app.state, "json_simplifier", None)
            if json_simplifier and json_simplifier.should_process("video"):
                result_dict = {"result": result}
                processed = json_simplifier.process(result_dict, "video")
                
                # If plain text explanation is available, add it to results
                if "plain_explanation" in processed:
                    result["plain_explanation"] = processed["plain_explanation"]
        
        return {
            "status": "completed",
            "result": result,
            "message": task.get("message", "Task completed successfully")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task result: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving task result: {str(e)}"
        )