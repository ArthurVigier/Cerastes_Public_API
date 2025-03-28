from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
import traceback
from .response_models import ErrorResponse

logger = logging.getLogger("cerastes.api")

class APIError(Exception):
    """Custom exception for API errors"""
    def __init__(self, message: str, status_code: int = 400, details: str = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

def register_exception_handlers(app: FastAPI):
    """Registers exception handlers for the FastAPI application"""
    
    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError):
        """Handler for custom API errors"""
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.message,
                details=exc.details,
                status_code=exc.status_code
            ).dict()
        )

    @app.exception_handler(404)
    async def handle_not_found(request: Request, exc: Exception):
        """Handler for 404 errors"""
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="Resource not found", 
                status_code=404
            ).dict()
        )

    @app.exception_handler(405)
    async def handle_method_not_allowed(request: Request, exc: Exception):
        """Handler for 405 errors"""
        return JSONResponse(
            status_code=405,
            content=ErrorResponse(
                error="Method not allowed", 
                status_code=405
            ).dict()
        )

    @app.exception_handler(500)
    async def handle_server_error(request: Request, exc: Exception):
        """Handler for server errors"""
        logger.error(f"Server error: {str(exc)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Internal server error", 
                status_code=500
            ).dict()
        )
    
    # FastAPI doesn't need an explicit handler for 400 like Flask
    # as it automatically generates 422 error responses for validation errors