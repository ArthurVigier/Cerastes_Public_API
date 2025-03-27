"""
Router for task management
---------------------------------
This module implements routes for tracking and managing asynchronous tasks.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

# Import response models
from .response_models import (
    TaskStatusResponse,
    TaskListResponse,
    SuccessResponse,
    ErrorResponse
)

# Import task manager
from inference_engine import (
    get_task_status,
    list_tasks,
    cancel_task,
    delete_task,
    TaskNotFoundException
)

# Import for authentication
from auth import get_current_active_user, User

# Logging configuration
logger = logging.getLogger("api.tasks")

# Create router
task_router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        500: {"model": ErrorResponse, "description": "Server error"}
    }
)

@task_router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves the status of a task"""
    task = get_task_status(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Check that the user has access to this task
    if not current_user.is_admin and task.get("user_id") != current_user.username:
        raise HTTPException(status_code=403, detail="You are not authorized to access this task")
    
    return task

@task_router.get("", response_model=TaskListResponse)
async def list_user_tasks(
    limit: int = 10,
    offset: int = 0,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Lists the user's tasks"""
    # If admin, don't filter by user
    user_filter = None if current_user.is_admin else current_user.username
    
    tasks_result = list_tasks(
        user_id=user_filter,
        task_type=task_type,
        status=status,
        limit=limit,
        offset=offset
    )
    
    return TaskListResponse(
        total=tasks_result.get("total", 0),
        limit=tasks_result.get("limit", limit),
        offset=tasks_result.get("offset", offset),
        tasks=tasks_result.get("tasks", {})
    )

@task_router.delete("/{task_id}", response_model=SuccessResponse)
async def cancel_user_task(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Cancels an ongoing task"""
    task = get_task_status(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Check that the user has access to this task
    if not current_user.is_admin and task.get("user_id") != current_user.username:
        raise HTTPException(status_code=403, detail="You are not authorized to cancel this task")
    
    result = cancel_task(task_id)
    
    if result:
        return SuccessResponse(
            success=True,
            message=f"Task {task_id} canceled successfully"
        )
    else:
        return SuccessResponse(
            success=False,
            message=f"Unable to cancel task {task_id}, it may already be completed"
        )