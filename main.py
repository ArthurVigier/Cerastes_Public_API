"""
Main entry point for the Cerastes API
-----------------------------------------
This module initializes the FastAPI application and mounts the various routers.
"""

import os
import logging
import time
import traceback
from pathlib import Path
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

# Importing routers
from api import (
    health_router,
    error_handlers,
    inference_router,
    transcription_router, 
    video_router,
    subscription_router,
    task_router,
    auth_router
)

# Importing middlewares
from middleware import APIKeyMiddleware
from middleware.translation_middleware import TranslationMiddleware
from middleware.cache_middleware import CacheMiddleware
from middleware.security_middleware import SecurityMiddleware
from middleware.rate_limit_middleware import RateLimitMiddleware
from middleware.failover_middleware import FailoverMiddleware

# Importing configuration
from config import setup_logging, app_config, model_config, api_config

# Initial logging configuration
setup_logging()
logger = logging.getLogger("api.main")

# Creating necessary directories
for directory in ["inference_results", "uploads", "results", "logs", "cache", "translation_models"]:
    Path(directory).mkdir(parents=True, exist_ok=True)

# FastAPI application initialization
app = FastAPI(
    title="Cerastes API",
    description="API for advanced analysis of multimedia and textual content",
    version=app_config.get("version", "1.0.0"),
    docs_url=None,  # Disabled by default, redirected to /api/docs
    redoc_url=None,  # Disabled by default, redirected to /api/redoc
    openapi_url="/api/openapi.json"
)

# Common excluded paths configuration
common_exclude_paths = [
    "/api/health", 
    "/auth/token", 
    "/auth/register", 
    "/api/docs", 
    "/api/redoc", 
    "/api/openapi.json",
    "/static"
]
common_exclude_prefixes = ["/static/", "/docs/", "/assets/"]

# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware - First in the chain to protect all requests
app.add_middleware(
    SecurityMiddleware,
    enable_xss_protection=True,
    enable_hsts=True,
    enable_content_type_options=True,
    enable_frame_options=True,
    enable_referrer_policy=True,
    enable_csp=True,
    enable_cors_protection=True,
    allowed_origins=cors_origins,
    allowed_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
)

# Rate limit middleware - Protection against abuse
app.add_middleware(
    RateLimitMiddleware,
    global_rate_limit=api_config.get("global_rate_limit", 1000),
    ip_rate_limit=api_config.get("ip_rate_limit", 100),
    api_key_rate_limit=api_config.get("api_key_rate_limit", 200),
    window_size=api_config.get("rate_limit_window", 60),
    exclude_paths=common_exclude_paths,
    exclude_prefixes=common_exclude_prefixes
)

# Cache middleware - Performance improvement
app.add_middleware(
    CacheMiddleware,
    ttl=api_config.get("cache_ttl", 300),
    max_size=api_config.get("cache_max_size", 1000),
    include_prefixes=["/api/inference/", "/api/video/", "/api/transcription/"],
    exclude_paths=common_exclude_paths + ["/api/tasks"],
    exclude_prefixes=common_exclude_prefixes,
    cache_query_params=True,
    cache_by_api_key=True
)

# Translation middleware - Internationalization
app.add_middleware(
    TranslationMiddleware,
    exclude_paths=common_exclude_paths,
    exclude_prefixes=common_exclude_prefixes,
    text_field_names=["text", "content", "prompt", "transcription", "question"]
)

# Failover middleware - Resilience
app.add_middleware(
    FailoverMiddleware,
    exclude_paths=common_exclude_paths,
    exclude_prefixes=common_exclude_prefixes,
    default_model_type="text"
)

# API key authentication middleware - Last in the middleware chain
app.add_middleware(
    APIKeyMiddleware,
    exclude_paths=common_exclude_paths,
    exclude_prefixes=["/static/", "/docs/"],
    admin_paths=["/admin/"]
)

# Custom routes for documentation
@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom route for Swagger UI."""
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title="Cerastes API - Documentation",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )

@app.get("/api/redoc", include_in_schema=False)
async def custom_redoc_html():
    """Custom route for ReDoc."""
    return get_redoc_html(
        openapi_url="/api/openapi.json",
        title="Cerastes API - Documentation ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
    )

# OpenAPI schema customization
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add contact and license information
    openapi_schema["info"]["contact"] = {
        "name": "Cerastes API Support",
        "url": "https://cerastes.ai/support",
        "email": "support@cerastes.ai"
    }
    
    openapi_schema["info"]["license"] = {
        "name": "Dual GPL/Commercial License",
        "url": "https://cerastes.ai/license"
    }
    
    # Customize tags
    openapi_schema["tags"] = [
        {
            "name": "health",
            "description": "Endpoints to check API status"
        },
        {
            "name": "inference",
            "description": "Endpoints for text inference"
        },
        {
            "name": "transcription",
            "description": "Endpoints for audio transcription"
        },
        {
            "name": "video",
            "description": "Endpoints for video analysis"
        },
        {
            "name": "tasks",
            "description": "Endpoints for task management"
        },
        {
            "name": "auth",
            "description": "Endpoints for authentication and authorization"
        },
        {
            "name": "subscription",
            "description": "Endpoints for subscription management"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Custom error handling
@app.middleware("http")
async def exception_handling(request: Request, call_next):
    """Middleware to handle global exceptions."""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        
        # Basic logging for successful requests
        process_time = time.time() - start_time
        logger.debug(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
        
        return response
    except Exception as e:
        # Detailed logging for exceptions
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(f"Path: {request.url.path}")
        logger.error(f"Method: {request.method}")
        logger.error(f"Client: {request.client.host if request.client else 'Unknown'}")
        logger.error(traceback.format_exc())
        
        # Return a structured error response
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "message": str(e),
                "type": type(e).__name__,
                "path": request.url.path
            }
        )

# Middleware for request logging
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Adds a header with processing time."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Mounting routers
app.include_router(health_router, prefix="/api")
app.include_router(inference_router, prefix="/api")
app.include_router(video_router, prefix="/api/video")
app.include_router(transcription_router, prefix="/api/transcription")
app.include_router(subscription_router, prefix="/api/subscription")
app.include_router(task_router, prefix="/api/tasks")
app.include_router(auth_router, prefix="/auth")

# Mounting error handlers
error_handlers.register_exception_handlers(app)

# Static files - only if directory exists
static_dir = Path("static")
if static_dir.exists() and static_dir.is_dir():
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Frontend - mounted at root
frontend_dir = Path("frontend/dist")
if frontend_dir.exists() and frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")

@app.on_event("startup")
async def startup_event():
    """Executed at application startup."""
    logger.info("=== Starting Cerastes API ===")
    
    # Initialize global resources (database, cache, etc.)
    try:
        # Database initialization
        from db.init_db import init_db
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Model manager initialization
    try:
        from model_manager import ModelManager
        ModelManager.initialize()
        logger.info("Model manager initialized successfully")
        
        # Preload models if configured
        if model_config.get("preload_models", False):
            logger.info("Model preloading requested...")
            preload_list = model_config.get("preload_list", [])
            for model_name in preload_list:
                try:
                    logger.info(f"Preloading model {model_name}...")
                    ModelManager.get_instance().load_model(model_name)
                except Exception as e:
                    logger.warning(f"Failed to preload model {model_name}: {str(e)}")
    except Exception as e:
        logger.error(f"Error initializing model manager: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Post-processors initialization
    try:
        from postprocessors.json_simplifier import JSONSimplifier
        from config import load_config
        
        config = load_config()
        json_simplifier = JSONSimplifier(config.get("postprocessing", {}).get("json_simplifier", {}))
        app.state.json_simplifier = json_simplifier
        
        if json_simplifier.enabled:
            logger.info(f"JSONSimplifier post-processor enabled for: {', '.join(json_simplifier.apply_to)}")
    except Exception as e:
        logger.error(f"Error initializing JSONSimplifier: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Advanced middleware initialization
    try:
        # Check model health for failover
        from middleware.failover_middleware import get_models_health
        health_report = get_models_health()
        logger.info(f"Failover middleware initialized with {len(health_report['models'])} configured models")
        
        # Cache initialization
        from middleware.cache_middleware import get_cache_stats
        logger.info(f"Cache middleware initialized: {get_cache_stats()}")
    except Exception as e:
        logger.warning(f"Error initializing advanced middleware: {str(e)}")
    
    # Startup information
    logger.info(f"Version: {app.version}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Log level: {os.getenv('LOG_LEVEL', 'INFO')}")
    
    # GPU verification
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        gpu_count = torch.cuda.device_count() if gpu_available else 0
        logger.info(f"GPU available: {gpu_available}, GPU count: {gpu_count}")
        
        if gpu_available:
            for i in range(gpu_count):
                logger.info(f"GPU {i}: {torch.cuda.get_device_name(i)}, Total memory: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
    except ImportError:
        logger.warning("PyTorch not available, operating in CPU-only mode")
    except Exception as e:
        logger.warning(f"Error checking GPUs: {str(e)}")
    
    # Data path verification
    for path_name, path in [
        ("Uploads", Path("uploads")),
        ("Results", Path("results")),
        ("Logs", Path("logs")),
        ("Cache", Path("cache")),
        ("Translation models", Path("translation_models"))
    ]:
        logger.info(f"{path_name}: {path.absolute()} ({path.exists() and path.is_dir() and os.access(path, os.W_OK)})") 
    
    # System prompts loading
    try:
        from config import get_system_prompts
        prompts, prompt_order = get_system_prompts()
        logger.info(f"System prompts loaded: {len(prompts)} prompts in order: {', '.join(prompt_order)}")
    except Exception as e:
        logger.error(f"Error loading system prompts: {str(e)}")
        logger.error(traceback.format_exc())
    
    # Mounted middleware verification
    middleware_list = [m.__class__.__name__ for m in app.user_middleware]
    logger.info(f"Active middlewares: {', '.join(middleware_list)}")
    
    logger.info("Cerastes API started successfully and ready to receive requests!")

@app.on_event("shutdown")
async def shutdown_event():
    """Executed at application shutdown."""
    logger.info("=== Stopping Cerastes API ===")
    
    # Release model resources
    try:
        from model_manager import ModelManager
        logger.info("Releasing models from memory...")
        ModelManager.cleanup()
    except Exception as e:
        logger.error(f"Error releasing models: {str(e)}")
    
    # Release middleware resources
    try:
        # Translator resources
        from middleware.translation_middleware import translation_manager
        logger.info("Releasing translation models...")
        translation_manager.close()
        
        # Cache resources
        from middleware.cache_middleware import invalidate_cache
        logger.info("Cleaning cache...")
        invalidate_cache()
        
        logger.info("Middleware resources released successfully")
    except Exception as e:
        logger.error(f"Error releasing middleware resources: {str(e)}")
    
    # Temporary files cleanup
    try:
        import shutil
        from datetime import datetime, timedelta
        
        # Delete temporary files older than 24h
        logger.info("Cleaning temporary files...")
        temp_dirs = ["uploads", "results/transcriptions", "cache"]
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for item in os.listdir(temp_dir):
                    item_path = os.path.join(temp_dir, item)
                    
                    # Check file age
                    if os.path.isfile(item_path):
                        mod_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                        if mod_time < cutoff_time:
                            try:
                                os.unlink(item_path)
                                logger.debug(f"Temporary file deleted: {item_path}")
                            except Exception as e:
                                logger.warning(f"Unable to delete {item_path}: {str(e)}")
    except Exception as e:
        logger.error(f"Error cleaning temporary files: {str(e)}")
    
    # Release CUDA resources
    try:
        import torch
        if torch.cuda.is_available():
            logger.info("Releasing CUDA memory...")
            torch.cuda.empty_cache()
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Error releasing CUDA memory: {str(e)}")
    
    # Close database connections
    try:
        from db import engine
        logger.info("Closing database connections...")
        engine.dispose()
    except Exception as e:
        logger.error(f"Error closing DB connections: {str(e)}")
    
    logger.info("Cerastes API shutdown completed")

# Entry point for direct execution
if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("RELOAD", "false").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port} (reload: {reload_enabled})")
    
    uvicorn.run(
        "main:app", 
        host=host, 
        port=port,
        reload=reload_enabled,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )