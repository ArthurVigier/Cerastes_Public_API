from flask import jsonify, Flask
import logging
import traceback
from .response_models import ErrorResponse

logger = logging.getLogger("cerastes.api")

class APIError(Exception):
    def __init__(self, message: str, status_code: int = 400, details: str = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

def register_error_handlers(app: Flask):
    @app.errorhandler(APIError)
    def handle_api_error(error):
        response = jsonify(
            ErrorResponse(
                error=error.message,
                details=error.details,
                status_code=error.status_code
            ).dict()
        )
        response.status_code = error.status_code
        return response

    @app.errorhandler(400)
    def handle_bad_request(error):
        return jsonify(ErrorResponse(
            error="Requête invalide", 
            status_code=400
        ).dict()), 400

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify(ErrorResponse(
            error="Ressource non trouvée", 
            status_code=404
        ).dict()), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify(ErrorResponse(
            error="Méthode non autorisée", 
            status_code=405
        ).dict()), 405

    @app.errorhandler(500)
    def handle_server_error(error):
        logger.error(f"Erreur serveur: {str(error)}")
        logger.error(traceback.format_exc())
        return jsonify(ErrorResponse(
            error="Erreur interne du serveur", 
            status_code=500
        ).dict()), 500