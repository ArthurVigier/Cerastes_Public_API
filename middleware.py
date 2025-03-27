from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Callable, List, Dict, Any, Optional
import time
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from auth import validate_api_key, check_usage_limits, record_usage, authorize_batch_processing, authorize_advanced_models
from auth_models import UsageRecord, ApiKey, ApiKeyLevel
from database import record_api_usage

# Configuration du logging
logger = logging.getLogger("auth_middleware")

class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware pour l'authentification par clé API et le suivi d'utilisation."""
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: List[str] = None,
        exclude_prefixes: List[str] = None,
        admin_paths: List[str] = None
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/docs", "/redoc", "/openapi.json", "/auth/token", "/auth/register"]
        self.exclude_prefixes = exclude_prefixes or ["/static/", "/assets/"]
        self.admin_paths = admin_paths or ["/auth/admin/"]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Mesurer le temps de traitement
        start_time = time.time()
        
        # Vérifier si le chemin est exclu de l'authentification
        path = request.url.path
        if self._is_excluded_path(path):
            response = await call_next(request)
            return response
        
        # Vérifier si le chemin nécessite des droits d'administrateur
        if self._is_admin_path(path) and not await self._check_admin_rights(request):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Accès réservé aux administrateurs"}
            )
        
        # Extraire et valider la clé API
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Clé API requise"}
            )
        
        try:
            # Valider la clé API
            from auth import get_api_key
            api_key_info = get_api_key(api_key)
            if not api_key_info:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Clé API invalide"}
                )
            
            # Vérifier si la clé est active
            if not api_key_info.is_active:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Clé API inactive"}
                )
            
            # Vérifier les autorisations spécifiques selon le chemin
            if "/api/batch" in path:
                try:
                    authorize_batch_processing(api_key_info)
                except HTTPException as e:
                    return JSONResponse(
                        status_code=e.status_code,
                        content={"detail": e.detail}
                    )
            
            # Vérifier l'accès aux modèles avancés si nécessaire
            if request.query_params.get("model") and request.query_params.get("model") != "default":
                try:
                    authorize_advanced_models(api_key_info)
                except HTTPException as e:
                    return JSONResponse(
                        status_code=e.status_code,
                        content={"detail": e.detail}
                    )
            
            # Vérifier les limites d'utilisation pour les requêtes qui envoient du texte
            if request.method == "POST" and ("/api/inference" in path or "/api/batch" in path):
                try:
                    # Extraire le contenu de la requête
                    body = await self._get_request_body(request)
                    
                    # Calculer la longueur du texte
                    text_length = 0
                    if "text" in body:
                        text_length = len(body["text"])
                    elif "texts" in body:
                        text_length = sum(len(t) for t in body["texts"])
                    
                    # Vérifier les limites
                    check_usage_limits(api_key_info, text_length)
                    
                except HTTPException as e:
                    return JSONResponse(
                        status_code=e.status_code,
                        content={"detail": e.detail}
                    )
                except Exception as e:
                    logger.error(f"Erreur lors de la vérification des limites: {e}")
            
            # Stocker la clé API dans la requête pour un accès ultérieur
            request.state.api_key_info = api_key_info
            
            # Exécuter le prochain middleware ou le gestionnaire de route
            response = await call_next(request)
            
            # Enregistrer l'utilisation
            processing_time = time.time() - start_time
            self._record_api_usage(request, response, api_key_info, processing_time)
            
            # Ajouter des headers d'information sur l'utilisation
            self._add_usage_headers(response, api_key_info)
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur dans le middleware API Key: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Erreur interne du serveur"}
            )
    
    def _is_excluded_path(self, path: str) -> bool:
        """Vérifie si le chemin est exclu de l'authentification."""
        if path in self.exclude_paths:
            return True
        
        for prefix in self.exclude_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _is_admin_path(self, path: str) -> bool:
        """Vérifie si le chemin nécessite des droits d'administrateur."""
        for admin_path in self.admin_paths:
            if path.startswith(admin_path):
                return True
        return False
    
    async def _check_admin_rights(self, request: Request) -> bool:
        """Vérifie si l'utilisateur a des droits d'administrateur."""
        # Cette méthode devrait vérifier le token JWT pour les droits admin
        # Pour simplifier, nous vérifions simplement si la clé API a un niveau ENTERPRISE
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return False
        
        from auth import get_api_key
        api_key_info = get_api_key(api_key)
        
        if not api_key_info:
            return False
        
        # Vérifier si l'utilisateur associé à la clé API a le rôle admin
        from database import get_user_by_id
        user = get_user_by_id(api_key_info.user_id)
        if not user:
            return False
        
        return "admin" in user.roles
    
    async def _get_request_body(self, request: Request) -> Dict[str, Any]:
        """Extrait le corps de la requête."""
        try:
            body_bytes = await request.body()
            body_str = body_bytes.decode('utf-8')
            return json.loads(body_str)
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction du corps de la requête: {e}")
            return {}
    
    def _record_api_usage(self, request: Request, response, api_key_info: ApiKey, processing_time: float):
        """Enregistre l'utilisation de l'API."""
        try:
            # Créer un enregistrement d'utilisation
            usage_record = UsageRecord(
                user_id=api_key_info.user_id,
                api_key_id=api_key_info.key,
                request_path=str(request.url.path),
                request_method=request.method,
                tokens_input=getattr(request.state, "tokens_input", 0),
                tokens_output=getattr(request.state, "tokens_output", 0),
                processing_time=processing_time,
                status_code=response.status_code
            )
            
            # Enregistrer l'utilisation
            record_api_usage(usage_record)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de l'utilisation: {e}")
    
    def _add_usage_headers(self, response, api_key_info: ApiKey):
        """Ajoute des headers d'information sur l'utilisation."""
        from auth import get_usage_limits
        try:
            # Récupérer les limites d'utilisation
            limits = get_usage_limits(api_key_info.level)
            
            # Calculer l'utilisation quotidienne et mensuelle
            today = time.strftime("%Y-%m-%d")
            current_month = time.strftime("%Y-%m")
            
            daily_usage = api_key_info.usage.get(today, 0)
            monthly_usage = sum(count for date, count in api_key_info.usage.items() if date.startswith(current_month))
            
            # Ajouter les headers
            response.headers["X-Rate-Limit-Limit-Day"] = str(limits.daily_requests)
            response.headers["X-Rate-Limit-Remaining-Day"] = str(max(0, limits.daily_requests - daily_usage))
            response.headers["X-Rate-Limit-Limit-Month"] = str(limits.monthly_requests)
            response.headers["X-Rate-Limit-Remaining-Month"] = str(max(0, limits.monthly_requests - monthly_usage))
            response.headers["X-Rate-Limit-Type"] = api_key_info.level
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout des headers d'utilisation: {e}")