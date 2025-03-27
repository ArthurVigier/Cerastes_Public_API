"""
Router for API health checking
----------------------------------------------
This module implements routes to check the status of the API and associated services.
"""

import os
import time
import platform
import logging
import psutil
from typing import Dict, Any, Optional

import torch
from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel

# Logging configuration
logger = logging.getLogger("api.health")

# Create router
health_router = APIRouter(
    prefix="/health",
    tags=["Health"],
)

# Pydantic models
class HealthResponse(BaseModel):
    """Model for health check response"""
    status: str
    version: str
    timestamp: float
    uptime: float

class HealthDetailedResponse(HealthResponse):
    """Model for detailed health check response"""
    environment: str
    system_info: Dict[str, Any]
    resources: Dict[str, Any]
    gpu_info: Optional[Dict[str, Any]] = None
    services: Dict[str, Any]

# Global variable for start time
start_time = time.time()

@health_router.get("", response_model=HealthResponse)
async def health_check():
    """Simple API health check"""
    return {
        "status": "ok",
        "version": os.getenv("VERSION", "1.0.0"),
        "timestamp": time.time(),
        "uptime": time.time() - start_time
    }

@health_router.get("/detailed", response_model=HealthDetailedResponse)
async def detailed_health_check():
    """Detailed health check of the API and system resources"""
    # System information
    system_info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "processor": platform.processor() or "Not available",
        "hostname": platform.node()
    }
    
    # Resource information
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    resources = {
        "cpu_percent": cpu_percent,
        "memory_total": memory.total,
        "memory_available": memory.available,
        "memory_percent": memory.percent,
        "disk_total": disk.total,
        "disk_free": disk.free,
        "disk_percent": disk.percent
    }
    
    # GPU information if available
    gpu_info = None
    try:
        if torch.cuda.is_available():
            gpu_info = {
                "available": True,
                "device_count": torch.cuda.device_count(),
                "current_device": torch.cuda.current_device(),
                "devices": []
            }
            
            for i in range(torch.cuda.device_count()):
                device_info = {
                    "name": torch.cuda.get_device_name(i),
                    "capability": torch.cuda.get_device_capability(i),
                    "properties": {
                        "total_memory": torch.cuda.get_device_properties(i).total_memory,
                    }
                }
                gpu_info["devices"].append(device_info)
                
                # Add usage statistics if available
                try:
                    import pynvml
                    pynvml.nvmlInit()
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    
                    device_info["utilization"] = {
                        "gpu_util": utilization.gpu,
                        "memory_util": utilization.memory,
                        "memory_used": memory_info.used,
                        "memory_free": memory_info.free
                    }
                except (ImportError, Exception) as e:
                    logger.debug(f"Unable to get detailed GPU statistics: {str(e)}")
    except Exception as e:
        logger.debug(f"Error retrieving GPU information: {str(e)}")
    
    # Services status
    services = check_services()
    
    return {
        "status": "ok" if all(s["status"] == "ok" for s in services.values()) else "degraded",
        "version": os.getenv("VERSION", "1.0.0"),
        "timestamp": time.time(),
        "uptime": time.time() - start_time,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "system_info": system_info,
        "resources": resources,
        "gpu_info": gpu_info,
        "services": services
    }

def check_services() -> Dict[str, Any]:
    """Checks the status of dependent services"""
    services = {}
    
    # Database check
    try:
        from database import get_db_connection
        db = get_db_connection()
        # Execute a simple query to check the connection
        db.command("ping")
        services["database"] = {
            "status": "ok",
            "message": "Database connection established"
        }
    except Exception as e:
        logger.warning(f"Database connection error: {str(e)}")
        services["database"] = {
            "status": "error",
            "message": f"Connection error: {str(e)}"
        }
    
    # Models check
    try:
        from model_manager import ModelManager
        manager = ModelManager.get_instance()
        services["models"] = {
            "status": "ok",
            "message": "Model manager initialized",
            "loaded_models": len(manager.loaded_models)
        }
    except Exception as e:
        logger.warning(f"Problem with model manager: {str(e)}")
        services["models"] = {
            "status": "warning",
            "message": f"Warning: {str(e)}"
        }
    
    # Filesystem check
    upload_dir = os.path.join(os.getcwd(), "uploads")
    results_dir = os.path.join(os.getcwd(), "results")
    
    if not os.path.exists(upload_dir) or not os.access(upload_dir, os.W_OK):
        services["filesystem"] = {
            "status": "error",
            "message": "Upload directory not writable"
        }
    elif not os.path.exists(results_dir) or not os.access(results_dir, os.W_OK):
        services["filesystem"] = {
            "status": "error",
            "message": "Results directory not writable"
        }
    else:
        services["filesystem"] = {
            "status": "ok",
            "message": "Filesystem is writable"
        }
    
    return services

@health_router.get("/ping")
async def ping():
    """Simple ping endpoint to check if the API is responding"""
    return {"ping": "pong"}

@health_router.get("/ready")
async def readiness_probe(response: Response):
    """
    Readiness probe for Kubernetes or other orchestrators
    Checks if the API is ready to receive requests
    """
    services = check_services()
    
    # If a critical service is in error, the API is not ready
    critical_services = ["database", "filesystem"]
    for service_name in critical_services:
        if service_name in services and services[service_name]["status"] == "error":
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "not_ready", "reason": services[service_name]["message"]}
    
    return {"status": "ready"}

@health_router.get("/live")
async def liveness_probe():
    """
    Liveness probe for Kubernetes or other orchestrators
    Checks if the API is alive
    """
    return {"status": "alive"}