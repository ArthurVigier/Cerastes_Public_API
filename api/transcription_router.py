"""
Router for audio and video transcription features
--------------------------------------------------------------
This module implements routes for transcribing audio and video files,
with or without speaker identification.
"""

import os
import logging
import time
import traceback
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import response models
from .response_models import (
    TranscriptionResponse,
    ErrorResponse,
    SuccessResponse,
    TaskResponse,
    TaskStatusResponse
)

# Import transcription functions
from transcription_models import (
    process_monologue,
    process_multiple_speakers,
    transcribe_external_audio,
    get_available_models,
    analyze_transcript
)

# Import for authentication
from auth import get_current_active_user, User

# Import configuration
from config import api_config, model_config, system_prompts

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
logger = logging.getLogger("api.transcription")

# Create router
transcription_router = APIRouter(
    prefix="/transcription",
    tags=["Transcription"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "File not found"},
        500: {"model": ErrorResponse, "description": "Server error"}
    }
)

# Configuration
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm', 'mp3', 'wav', 'ogg', 'flac', 'm4a'}
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results/transcriptions'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Pydantic models for responses
class ModelInfo(BaseModel):
    name: str
    description: str
    languages: List[str]
    size_mb: float
    is_multilingual: bool

class ModelsResponse(BaseModel):
    whisper: Dict[str, ModelInfo]
    diarization: Optional[Dict[str, ModelInfo]] = None

class AnalysisRequest(BaseModel):
    transcription: str
    language: Optional[str] = None
    analysis_type: Optional[str] = "general"

class TranscriptionAnalysisResponse(BaseModel):
    analysis: Dict[str, Any]
    plain_explanation: Optional[str] = None
    message: str

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

def create_output_filename(original_filename: str) -> str:
    """Creates a filename for the transcription output"""
    base_name = os.path.basename(original_filename)
    name_without_ext = os.path.splitext(base_name)[0]
    timestamp = int(time.time())
    return os.path.join(RESULTS_FOLDER, f"{name_without_ext}_{timestamp}.txt")

def formatted_analyze_transcript(transcription: str, language: Optional[str] = None, analysis_type: str = "general"):
    """Adapted version of analyze_transcript using prompt manager"""
    prompt_manager = get_prompt_manager()
    
    # Select prompt type based on analysis type
    prompt_key = f"transcription_{analysis_type}_analysis"
    fallback_prompt = "Analyze the following transcription: {text}"
    
    # Use formatted prompt with placeholder {text}
    if prompt_key in system_prompts:
        prompt = prompt_manager.format_prompt_direct(
            system_prompts[prompt_key], 
            text=transcription,
            language=language or "unknown"
        )
    else:
        # Fallback to default prompt if not found
        prompt = prompt_manager.format_prompt_direct(
            fallback_prompt,
            text=transcription
        )
    
    # Call analysis function with formatted prompt
    return analyze_transcript(prompt, language)

async def process_transcription_task(task_id: str, file_path: str, output_txt: str, 
                                     model_size: str, is_diarization: bool = False,
                                     huggingface_token: Optional[str] = None,
                                     analyze: bool = False,
                                     analysis_type: str = "general"):
    """Asynchronous function to process a transcription task in the background"""
    try:
        # Update status
        update_task(task_id, {
            "status": "running",
            "message": "Transcription in progress..."
        })
        
        # Initialize progress tracker
        progress_tracker = ProgressTracker(task_id)
        
        # Call appropriate function based on transcription type
        if is_diarization:
            result = process_multiple_speakers(
                file_path, 
                output_txt=output_txt,
                model_size=model_size,
                huggingface_token=huggingface_token,
                progress=progress_tracker
            )
        else:
            result = process_monologue(
                file_path, 
                output_txt=output_txt,
                model_size=model_size,
                progress=progress_tracker
            )
        
        # If analysis is requested, perform it
        if analyze and "transcription" in result:
            update_task(task_id, {
                "message": "Analyzing transcription..."
            })
            
            # Use formatted version of analysis
            analysis_result = formatted_analyze_transcript(
                result["transcription"],
                language=result.get("language"),
                analysis_type=analysis_type
            )
            
            # Add analysis to results
            result["analysis"] = analysis_result
            
        # Update with results
        update_task(task_id, {
            "status": "completed",
            "results": result,
            "message": "Transcription completed successfully"
        })
        
        logger.info(f"Transcription task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error during transcription task {task_id}: {str(e)}")
        logger.error(traceback.format_exc())
        update_task(task_id, {
            "status": "failed",
            "error": str(e),
            "message": f"Error: {str(e)}"
        })

@transcription_router.post('/monologue', response_model=TranscriptionResponse)
async def transcribe_monologue(
    request: Request,
    file: UploadFile = File(...),
    model_size: str = Form("medium"),
    current_user: User = Depends(get_current_active_user)
):
    """Transcribes a video or audio file (monologue mode)"""
    try:
        # Save uploaded file
        file_path = await save_uploaded_file(file)
        logger.info(f"File saved to {file_path}")
        
        # Create output file
        output_txt = create_output_filename(file_path)
        
        # Process transcription
        result = process_monologue(
            file_path, 
            output_txt=output_txt,
            model_size=model_size,
            progress=lambda progress, desc: logger.debug(f"Progress: {progress*100:.1f}% - {desc}")
        )
        
        # Apply JSONSimplifier post-processor if available
        json_simplifier = getattr(request.app.state, "json_simplifier", None)
        if json_simplifier and json_simplifier.should_process("transcription"):
            result_dict = {"result": result}
            processed = json_simplifier.process(result_dict, "transcription")
            result = processed.get("result", result)
            
            # If plain text explanation is available, add it to results
            if "plain_explanation" in processed:
                result["plain_explanation"] = processed["plain_explanation"]
        
        # Prepare response
        response = TranscriptionResponse(
            transcription=result["transcription"],
            language=result.get("language", ""),
            duration=result.get("duration", 0),
            segments=result.get("segments", []),
            file_path=output_txt,
            message="Transcription successful",
            plain_explanation=result.get("plain_explanation")
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during transcription: {str(e)}")

@transcription_router.post('/multiple_speakers', response_model=TranscriptionResponse)
async def transcribe_multiple_speakers(
    request: Request,
    file: UploadFile = File(...),
    model_size: str = Form("medium"),
    huggingface_token: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """Transcribes a video or audio file with speaker identification"""
    # Use provided token or environment one
    token = huggingface_token or os.environ.get('HUGGINGFACE_TOKEN') or model_config["diarization"]["huggingface_token"]
    
    if not token:
        raise HTTPException(
            status_code=400, 
            detail="A Hugging Face token is required for speaker identification"
        )
    
    try:
        # Save uploaded file
        file_path = await save_uploaded_file(file)
        logger.info(f"File saved to {file_path}")
        
        # Create output file
        output_txt = create_output_filename(file_path)
        
        # Process transcription with speaker identification
        result = process_multiple_speakers(
            file_path, 
            output_txt=output_txt,
            model_size=model_size,
            huggingface_token=token,
            progress=lambda progress, desc: logger.debug(f"Progress: {progress*100:.1f}% - {desc}")
        )
        
        # Apply JSONSimplifier post-processor if available
        json_simplifier = getattr(request.app.state, "json_simplifier", None)
        if json_simplifier and json_simplifier.should_process("transcription"):
            result_dict = {"result": result}
            processed = json_simplifier.process(result_dict, "transcription")
            result = processed.get("result", result)
            
            # If plain text explanation is available, add it to results
            if "plain_explanation" in processed:
                result["plain_explanation"] = processed["plain_explanation"]
        
        # Prepare response
        response = TranscriptionResponse(
            transcription=result["transcription"],
            language=result.get("language", ""),
            duration=result.get("duration", 0),
            segments=result.get("segments", []),
            file_path=output_txt,
            speakers=result.get("speakers", []),
            message="Transcription with speaker identification successful",
            plain_explanation=result.get("plain_explanation")
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during transcription with speaker identification: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error during transcription with speaker identification: {str(e)}"
        )

@transcription_router.post('/audio', response_model=TranscriptionResponse)
async def transcribe_audio(
    request: Request,
    file: UploadFile = File(...),
    model_size: str = Form("medium"),
    current_user: User = Depends(get_current_active_user)
):
    """Transcribes an existing audio file"""
    # Check extension
    if not file.filename.lower().endswith(('.mp3', '.wav', '.ogg', '.flac', '.m4a')):
        raise HTTPException(
            status_code=400, 
            detail="File must be in audio format (mp3, wav, ogg, flac, m4a)"
        )
    
    try:
        # Save uploaded file
        audio_path = await save_uploaded_file(file)
        logger.info(f"Audio file saved to {audio_path}")
        
        # Create output file
        output_txt = create_output_filename(audio_path)
        
        # Transcribe audio
        result = transcribe_external_audio(
            audio_path, 
            model_size=model_size,
            output_txt=output_txt,
            progress=lambda progress, desc: logger.debug(f"Progress: {progress*100:.1f}% - {desc}")
        )
        
        # Apply JSONSimplifier post-processor if available
        json_simplifier = getattr(request.app.state, "json_simplifier", None)
        if json_simplifier and json_simplifier.should_process("transcription"):
            result_dict = {"result": result}
            processed = json_simplifier.process(result_dict, "transcription")
            result = processed.get("result", result)
            
            # If plain text explanation is available, add it to results
            if "plain_explanation" in processed:
                result["plain_explanation"] = processed["plain_explanation"]
        
        # Prepare response
        response = TranscriptionResponse(
            transcription=result["transcription"],
            language=result.get("language", ""),
            duration=result.get("duration", 0),
            segments=result.get("segments", []),
            file_path=output_txt,
            message="Audio transcription successful",
            plain_explanation=result.get("plain_explanation")
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during audio transcription: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during audio transcription: {str(e)}")

@transcription_router.post('/analyze', response_model=TranscriptionAnalysisResponse)
async def analyze_transcription(
    request: Request,
    analysis_req: AnalysisRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Analyzes an existing transcription"""
    try:
        # Use formatted version of analysis with prompt manager
        analysis = formatted_analyze_transcript(
            analysis_req.transcription,
            language=analysis_req.language,
            analysis_type=analysis_req.analysis_type
        )
        
        # Apply JSONSimplifier post-processor if available
        result = {"analysis": analysis, "message": "Transcription analysis successful"}
        json_simplifier = getattr(request.app.state, "json_simplifier", None)
        if json_simplifier and json_simplifier.should_process("transcription"):
            processed = json_simplifier.process(result, "transcription")
            
            # If plain text explanation is available, add it to results
            if "plain_explanation" in processed:
                result["plain_explanation"] = processed["plain_explanation"]
        
        # Prepare response
        response = TranscriptionAnalysisResponse(**result)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during transcription analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during transcription analysis: {str(e)}")

@transcription_router.post('/async_transcribe', response_model=TaskResponse)
async def async_transcribe(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model_size: str = Form("medium"),
    enable_diarization: bool = Form(False),
    analyze: bool = Form(False),
    analysis_type: str = Form("general"),
    huggingface_token: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """Starts an asynchronous transcription (in background)"""
    try:
        # Save uploaded file
        file_path = await save_uploaded_file(file)
        logger.info(f"File saved to {file_path} for asynchronous transcription")
        
        # Create output file
        output_txt = create_output_filename(file_path)
        
        # Check if diarization is requested and token is available
        if enable_diarization:
            token = huggingface_token or os.environ.get('HUGGINGFACE_TOKEN') or model_config["diarization"]["huggingface_token"]
            if not token:
                raise HTTPException(
                    status_code=400, 
                    detail="A Hugging Face token is required for speaker identification"
                )
            
            # Define task type
            task_type = TaskType.TRANSCRIPTION_MULTISPEAKER
        else:
            token = None
            task_type = TaskType.TRANSCRIPTION_MONOLOGUE
        
        # Task parameters
        task_params = {
            "file_path": file_path,
            "output_txt": output_txt,
            "model_size": model_size,
            "is_diarization": enable_diarization,
            "huggingface_token": token,
            "analyze": analyze,
            "analysis_type": analysis_type
        }
        
        # Create task
        task_id = create_task(
            task_type=task_type,
            user_id=current_user.username,
            params=task_params
        )
        
        # Launch task in background
        background_tasks.add_task(
            process_transcription_task,
            task_id=task_id,
            file_path=file_path,
            output_txt=output_txt,
            model_size=model_size,
            is_diarization=enable_diarization,
            huggingface_token=token,
            analyze=analyze,
            analysis_type=analysis_type
        )
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message="Transcription task launched successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error launching asynchronous transcription: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error launching asynchronous transcription: {str(e)}"
        )

@transcription_router.get('/task/{task_id}/result', response_model=None)
async def get_task_result(
    task_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves the result of a transcription task"""
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
            if json_simplifier and json_simplifier.should_process("transcription"):
                result_dict = {"result": result}
                processed = json_simplifier.process(result_dict, "transcription")
                
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

@transcription_router.get('/models', response_model=ModelsResponse)
async def get_models():
    """Retrieves information about available transcription models"""
    try:
        models_info = get_available_models()
        
        return ModelsResponse(
            whisper=models_info.get("whisper", {}),
            diarization=models_info.get("diarization", {})
        )
        
    except Exception as e:
        logger.error(f"Error retrieving models: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving models: {str(e)}")

@transcription_router.get('/allowed_extensions')
async def get_allowed_extensions():
    """Retrieves the list of allowed audio file extensions"""
    return {
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "max_upload_size_mb": model_config["audio"]["max_upload_size_mb"]
    }