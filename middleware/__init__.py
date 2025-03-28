# Importer et exposer le middleware APIKey depuis le fichier parent
import sys
import os

# Ajouter le répertoire parent au path pour importer le module middleware.py
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Importer depuis le fichier middleware.py
from middleware import APIKeyMiddleware

# Importer les autres middlewares du package
from .security_middleware import SecurityMiddleware
from .rate_limit_middleware import RateLimitMiddleware
from .cache_middleware import CacheMiddleware
from .translation_middleware import TranslationMiddleware
from .failover_middleware import FailoverMiddleware, get_models_health

# Exposer tous ces middlewares pour faciliter l'importation
__all__ = [
    'APIKeyMiddleware',
    'SecurityMiddleware',
    'RateLimitMiddleware',
    'CacheMiddleware',
    'TranslationMiddleware',
    'FailoverMiddleware',
    'get_models_health'
]