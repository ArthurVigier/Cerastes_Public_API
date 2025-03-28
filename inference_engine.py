"""
Multi-model Inference Engine
-------------------------------
This module manages inferences with different language and AI models,
as well as asynchronous task management.
"""

import os
import time
import json
import logging
import traceback
import threading
import asyncio
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Union, Any, Tuple, Callable, Type
from model_manager import ModelManager, ModelType
from config import inference_config, system_prompts
from utils.segmentation import split_text_into_segments
from utils.prompt_manager import get_prompt_manager

# Logging configuration
logger = logging.getLogger("inference_engine")

# Results storage directory
RESULTS_DIR = Path(inference_config.get("result_storage_dir", "inference_results"))
os.makedirs(RESULTS_DIR, exist_ok=True)

# Exception classes
class InferenceError(Exception):
    """Base error for inference errors"""
    pass

class ModelLoadError(InferenceError):
    """Error when loading a model"""
    pass

class TaskNotFoundException(InferenceError):
    """Task not found"""
    pass

class ModelNotFoundException(InferenceError):
    """Model not found"""
    pass

# Task types for the management system
class TaskType(str, Enum):
    TEXT_INFERENCE = "text_inference"
    IMAGE_GENERATION = "image_generation"
    EMBEDDING = "embedding"
    TRANSCRIPTION_MONOLOGUE = "transcription_monologue"
    TRANSCRIPTION_MULTISPEAKER = "transcription_multispeaker"
    VIDEO_MANIPULATION = "video_manipulation_analysis"
    VIDEO_NONVERBAL = "video_nonverbal_analysis"
    BATCH = "batch"
    SYSTEM_FINAL = "system_final"  # Nouveau type pour l'inférence finale

# Centralized task manager
class TaskManager:
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        # Centralized task dictionary
        self.tasks = {}
        self.task_lock = threading.Lock()
    
    def create_task(self, task_type: Union[TaskType, str], user_id: str, params: Dict[str, Any]) -> str:
        """
        Creates a new task with a unique ID.
        
        Args:
            task_type: Task type (see TaskType enum)
            user_id: ID of the user who owns the task
            params: Task-specific parameters
            
        Returns:
            task_id: Unique task identifier
        """
        import uuid
        import time
        
        task_id = str(uuid.uuid4())
        
        with self.task_lock:
            self.tasks[task_id] = {
                "task_id": task_id,
                "type": task_type,
                "status": "pending",
                "user_id": user_id,
                "created_at": time.time(),
                "started_at": None,
                "completed_at": None,
                "progress": 0,
                "message": "Task waiting for processing",
                "params": params
            }
        
        logger.info(f"New task created: {task_id} of type {task_type} for user {user_id}")
        return task_id
    
    def update_task(self, task_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Updates the state of an existing task.
        
        Args:
            task_id: Task identifier
            update_data: Data to update
            
        Returns:
            bool: True if update successful, False otherwise
        """
        with self.task_lock:
            if task_id not in self.tasks:
                logger.warning(f"Attempt to update non-existent task: {task_id}")
                return False
            
            # Prevent modification of certain fields
            if "task_id" in update_data:
                del update_data["task_id"]
            if "user_id" in update_data:
                del update_data["user_id"]
            if "created_at" in update_data:
                del update_data["created_at"]
            
            # Update specific fields
            for key, value in update_data.items():
                self.tasks[task_id][key] = value
            
            # If status changes to "running", set started_at
            if update_data.get("status") == "running" and self.tasks[task_id].get("started_at") is None:
                self.tasks[task_id]["started_at"] = time.time()
                
            # If status changes to "completed" or "failed", set completed_at
            if update_data.get("status") in ["completed", "failed"] and self.tasks[task_id].get("completed_at") is None:
                self.tasks[task_id]["completed_at"] = time.time()
                self.tasks[task_id]["progress"] = 100
        
        return True
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves information about a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dict: Task information or None if it doesn't exist
        """
        with self.task_lock:
            if task_id in self.tasks:
                return self.tasks[task_id].copy()
            return None
    
    def list_tasks(self, user_id: Optional[str] = None, task_type: Optional[str] = None, 
                  status: Optional[str] = None, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        Lists tasks with filtering and pagination.
        
        Args:
            user_id: Filter by user
            task_type: Filter by task type
            status: Filter by status
            limit: Maximum number of tasks to return
            offset: Pagination offset
            
        Returns:
            Dict: Information about filtered tasks
        """
        with self.task_lock:
            filtered_tasks = {}
            
            for task_id, task in self.tasks.items():
                # Apply filters
                if user_id is not None and task.get("user_id") != user_id:
                    continue
                if task_type is not None and task.get("type") != task_type:
                    continue
                if status is not None and task.get("status") != status:
                    continue
                
                filtered_tasks[task_id] = task.copy()
            
            # Sort by creation date (newest first)
            sorted_tasks = sorted(
                filtered_tasks.items(),
                key=lambda x: x[1].get("created_at", 0),
                reverse=True
            )
            
            # Apply pagination
            paginated_tasks = dict(sorted_tasks[offset:offset+limit])
            
            return {
                "total": len(filtered_tasks),
                "limit": limit,
                "offset": offset,
                "tasks": paginated_tasks
            }
    
    def delete_task(self, task_id: str) -> bool:
        """
        Deletes a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        with self.task_lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                return True
            return False
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancels an ongoing task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            bool: True if cancellation successful, False otherwise
        """
        with self.task_lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task["status"] in ["pending", "running"]:
                task["status"] = "cancelled"
                task["message"] = "Task canceled by user"
                task["completed_at"] = time.time()
                return True
            
            # Can't cancel an already completed task
            return False
    
    def update_progress(self, task_id: str, progress: float, message: Optional[str] = None) -> bool:
        """
        Updates the progress of a task.
        
        Args:
            task_id: Task identifier
            progress: Progress (0-100)
            message: Optional message
            
        Returns:
            bool: True if update successful, False otherwise
        """
        update_data = {"progress": float(progress)}
        if message:
            update_data["message"] = message
        
        return self.update_task(task_id, update_data)

# Interface functions to access the task manager
def create_task(task_type: Union[TaskType, str], user_id: str, params: Dict[str, Any]) -> str:
    """Creates a new task with the centralized manager"""
    return TaskManager.get_instance().create_task(task_type, user_id, params)

def update_task(task_id: str, update_data: Dict[str, Any]) -> bool:
    """Updates an existing task"""
    return TaskManager.get_instance().update_task(task_id, update_data)

def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the status of a task"""
    task = TaskManager.get_instance().get_task(task_id)
    if not task:
        return None
    return task

def list_tasks(user_id: Optional[str] = None, task_type: Optional[str] = None,
              status: Optional[str] = None, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    """Lists tasks according to specified criteria"""
    return TaskManager.get_instance().list_tasks(user_id, task_type, status, limit, offset)

def cancel_task(task_id: str) -> bool:
    """Cancels an ongoing task"""
    return TaskManager.get_instance().cancel_task(task_id)

def delete_task(task_id: str) -> bool:
    """Deletes a task"""
    return TaskManager.get_instance().delete_task(task_id)

def update_progress(task_id: str, progress: float, message: Optional[str] = None) -> bool:
    """Updates the progress of a task"""
    return TaskManager.get_instance().update_progress(task_id, progress, message)

# Progress tracking class to use for transcriptions and video processing
class ProgressTracker:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.progress = 0
        self.message = "Initializing..."
        
    def __call__(self, progress: float, desc: str = None):
        self.progress = float(progress) * 100
        if desc:
            self.message = desc
        
        # Update task status
        update_progress(self.task_id, self.progress, self.message)

# Class for text inference with standardized prompt management
class TextInference:
    def __init__(self):
        self.model_manager = ModelManager.get_instance()
        self.prompt_manager = get_prompt_manager()
        
    def generate(self, 
                 prompt_name: str, 
                 input_text: str, 
                 model_name: Optional[str] = None,
                 max_tokens: Optional[int] = None,
                 temperature: Optional[float] = None,
                 progress_callback: Optional[Callable] = None,
                 **prompt_kwargs) -> str:
        """
        Generates text using the specified prompt and model.
        
        Args:
            prompt_name: Name of the system prompt to use
            input_text: Input text to analyze
            model_name: Name of the model to use (otherwise uses default model)
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for generation
            progress_callback: Callback function for progress
            **prompt_kwargs: Additional arguments for prompt formatting
            
        Returns:
            The generated text
        """
        try:
            # Get the model
            model = self.model_manager.get_model("llm", model_name)
            if not model:
                raise ModelNotFoundException(f"Model not found: {model_name}")
            
            # Prepare generation parameters
            gen_params = {
                "max_tokens": max_tokens or inference_config.get("max_new_tokens", 1024),
                "temperature": temperature or inference_config.get("temperature", 0.7),
            }
            
            # Prepare formatted prompt with prompt manager
            full_prompt_kwargs = {"text": input_text, **prompt_kwargs}
            
            # Format prompt using prompt manager
            if prompt_name in system_prompts:
                prompt = self.prompt_manager.format_prompt_direct(
                    system_prompts[prompt_name],
                    **full_prompt_kwargs
                )
            else:
                # Fallback to default prompt
                logger.warning(f"Prompt '{prompt_name}' not found, using default prompt")
                default_prompt = "Analyze the following text: {text}"
                prompt = self.prompt_manager.format_prompt_direct(
                    default_prompt,
                    **full_prompt_kwargs
                )
            
            # Log the inference
            logger.info(f"Inference with model {model_name}, prompt: {prompt_name}")
            
            # Execute inference
            response = model.generate(prompt, **gen_params)
            
            return response
            
        except Exception as e:
            logger.error(f"Error during text inference: {str(e)}")
            logger.error(traceback.format_exc())
            raise InferenceError(f"Inference error: {str(e)}")

# Function to execute inference with prompt manager
async def run_inference_with_prompt_manager(
    task_id: str,
    user_input: str,
    prompt_name: str,
    model_name: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    **prompt_kwargs
) -> Dict[str, Any]:
    """
    Executes text inference using the prompt manager.
    
    Args:
        task_id: Task ID
        user_input: User input text
        prompt_name: Name of system prompt to use
        model_name: Name of model to use (otherwise default model)
        max_tokens: Maximum number of tokens to generate
        temperature: Temperature for generation
        **prompt_kwargs: Additional arguments for prompt formatting
        
    Returns:
        Dictionary with inference result
    """
    try:
        # Status update
        update_task(task_id, {
            "status": "running",
            "message": "Inference in progress..."
        })
        
        # Initialize inference object
        text_inference = TextInference()
        
        # Generate text
        response = text_inference.generate(
            prompt_name=prompt_name,
            input_text=user_input,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            progress_callback=lambda p: update_progress(task_id, p),
            **prompt_kwargs
        )
        
        # Save result
        result_file = RESULTS_DIR / f"{task_id}.json"
        result = {
            "prompt": prompt_name,
            "input": user_input,
            "output": response,
            "model": model_name,
            "timestamp": time.time()
        }
        
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Update task
        update_task(task_id, {
            "status": "completed",
            "results": result,
            "message": "Inference completed successfully"
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error during inference for task {task_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Update error status
        update_task(task_id, {
            "status": "failed",
            "error": str(e),
            "message": f"Error: {str(e)}"
        })
        
        return {
            "error": str(e),
            "status": "failed"
        }

# Function to execute inference task (compatible with existing code)
async def run_inference(task_id: str, task_type: str, params: Dict[str, Any]) -> None:
    """
    Executes an inference task in the background.
    
    Args:
        task_id: Task identifier
        task_type: Task type
        params: Task parameters
    """
    # Status update
    update_task(task_id, {
        "status": "running",
        "message": "Inference in progress..."
    })
    
    try:
        # Initialize prompt manager
        prompt_manager = get_prompt_manager()
        
        # Specific logic based on task type
        if task_type == "text":
            # Existing text inference code...
            # [Code existant]
            
        elif task_type == "image":
            # Existing image generation code...
            # [Code existant]
            
        elif task_type == "embedding":
            # Existing embedding code...
            # [Code existant]
            
        elif task_type == "chain":
            # Chain inference with sequenced prompts
            text = params.get("text", "")
            prompt_sequence = params.get("prompt_sequence", [])
            model = params.get("model")
            max_tokens = params.get("max_tokens", 1024)
            temperature = params.get("temperature", 0.7)
            
            # Execute chain inference
            result = await run_inference_chain(
                task_id=task_id,
                input_text=text,
                prompt_names=prompt_sequence,
                model_name=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
        elif task_type == "system_final":
            # New system_final inference type
            task_dependencies = params.get("task_dependencies", {})
            model = params.get("model")
            max_tokens = params.get("max_tokens", 1024)
            temperature = params.get("temperature", 0.7)
            
            # Execute system_final inference
            result = await run_system_final_inference(
                task_id=task_id,
                task_dependencies=task_dependencies,
                model_name=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
        else:
            raise ValueError(f"Unsupported task type: {task_type}")
        
        # Final status update is handled by the specific task runners
        
    except Exception as e:
        logger.error(f"Error during inference for task {task_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Update error status
        update_task(task_id, {
            "status": "failed",
            "error": str(e),
            "message": f"Error: {str(e)}"
        })

# Function to execute inference chain with sequential prompts
async def run_inference_chain(
    task_id: str,
    input_text: str,
    prompt_names: List[str],
    model_name: Optional[str] = None,
    **gen_params
) -> Dict[str, Any]:
    """
    Executes a chain of inferences using a sequence of prompts.
    
    Args:
        task_id: Task ID
        input_text: Initial input text
        prompt_names: List of prompt names to use in order
        model_name: Name of model to use
        **gen_params: Generation parameters
        
    Returns:
        Dictionary with results of each step and final result
    """
    try:
        # Status update
        update_task(task_id, {
            "status": "running",
            "message": "Inference chain in progress..."
        })
        
        # Initialize inference object
        text_inference = TextInference()
        
        # Intermediate results
        intermediate_results = []
        current_text = input_text
        
        # Execute each step in the chain
        for i, prompt_name in enumerate(prompt_names):
            # Update progress
            progress = (i / len(prompt_names)) * 100
            update_progress(task_id, progress, f"Step {i+1}/{len(prompt_names)}: {prompt_name}")
            
            # Generate text for this step
            step_result = text_inference.generate(
                prompt_name=prompt_name,
                input_text=current_text,
                model_name=model_name,
                **gen_params
            )
            
            # Store intermediate result
            intermediate_results.append({
                "step": i+1,
                "prompt": prompt_name,
                "input": current_text,
                "output": step_result
            })
            
            # Use output as input for next step
            current_text = step_result
        
        # Final result
        final_result = {
            "input": input_text,
            "output": current_text,
            "steps": intermediate_results,
            "model": model_name,
            "timestamp": time.time()
        }
        
        # Save result
        result_file = RESULTS_DIR / f"{task_id}_chain.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)
        
        # Update task
        update_task(task_id, {
            "status": "completed",
            "results": final_result,
            "message": "Inference chain completed successfully"
        })
        
        return final_result
        
    except Exception as e:
        logger.error(f"Error during inference chain for task {task_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Update error status
        update_task(task_id, {
            "status": "failed",
            "error": str(e),
            "message": f"Error: {str(e)}"
        })
        
        return {
            "error": str(e),
            "status": "failed",
            "steps_completed": len(intermediate_results)
        }
async def run_system_final_inference(
    task_id: str,
    task_dependencies: Dict[str, str],
    model_name: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None
) -> Dict[str, Any]:
    """
    Exécute une inférence finale utilisant les résultats de tâches précédentes.
    
    Args:
        task_id: ID de la tâche
        task_dependencies: Dictionnaire des IDs des tâches précédentes {task_id_1, task_id_2, task_id_1_2, task_id_1_2_1}
        model_name: Nom du modèle à utiliser
        max_tokens: Nombre maximum de tokens à générer
        temperature: Température pour la génération
        
    Returns:
        Dictionnaire avec le résultat de l'inférence finale
    """
    try:
        # Mise à jour du statut
        update_task(task_id, {
            "status": "running",
            "message": "Inférence finale en cours..."
        })
        
        # Récupérer les résultats des tâches dépendantes
        session_results = {}
        for key, dep_task_id in task_dependencies.items():
            task_info = get_task_status(dep_task_id)
            if not task_info:
                raise TaskNotFoundException(f"Tâche dépendante non trouvée: {dep_task_id}")
                
            # Extraire le résultat de la tâche précédente
            task_result = task_info.get("results", {})
            if "text" in task_result:
                session_results[key.replace("task_id_", "session_")] = task_result["text"]
            elif "final_result" in task_result:
                session_results[key.replace("task_id_", "session_")] = task_result["final_result"]
            else:
                # Fallback pour d'autres types de résultats
                result_text = json.dumps(task_result)
                session_results[key.replace("task_id_", "session_")] = result_text
        
        # Initialiser l'objet d'inférence
        text_inference = TextInference()
        
        # Générer le texte final en utilisant les résultats intermédiaires comme placeholders
        final_result = text_inference.generate(
            prompt_name="system_final",
            input_text="",  # Non utilisé car on utilise des placeholders spécifiques
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            **session_results  # Injecte les résultats des sessions comme placeholders
        )
        
        # Enregistrer le résultat
        result_file = RESULTS_DIR / f"{task_id}_final.json"
        result = {
            "final_result": final_result,
            "dependencies": task_dependencies,
            "model": model_name,
            "timestamp": time.time()
        }
        
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Mettre à jour la tâche
        update_task(task_id, {
            "status": "completed",
            "results": result,
            "message": "Inférence finale terminée avec succès"
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Erreur pendant l'inférence finale pour la tâche {task_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Mettre à jour le statut d'erreur
        update_task(task_id, {
            "status": "failed",
            "error": str(e),
            "message": f"Erreur: {str(e)}"
        })
        
        return {
            "error": str(e),
            "status": "failed"
        }