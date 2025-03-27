"""
Module de post-processeurs pour l'API Cerastes
---------------------------------------------
Ce module fournit différents post-processeurs pour améliorer et transformer
les résultats des inférences et des analyses.

Classes exportées:
    - JSONSimplifier: Convertit les réponses JSON complexes en texte explicatif clair
"""

import logging
from typing import Dict, Any, List, Optional, Type

# Import des post-processeurs disponibles
from .json_simplifier import JSONSimplifier

# Configuration du logging
logger = logging.getLogger("postprocessors")

# Dictionnaire des post-processeurs disponibles
available_postprocessors = {
    "json_simplifier": JSONSimplifier
}

def get_postprocessor(name: str, config: Dict[str, Any]) -> Optional[Any]:
    """
    Récupère une instance d'un post-processeur par son nom.
    
    Args:
        name: Nom du post-processeur à instancier
        config: Configuration à utiliser pour l'initialisation
    
    Returns:
        Instance du post-processeur ou None si non trouvé
    """
    if name not in available_postprocessors:
        logger.warning(f"Post-processeur '{name}' non trouvé")
        return None
    
    try:
        processor_class = available_postprocessors[name]
        return processor_class(config)
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du post-processeur '{name}': {str(e)}")
        return None

def list_postprocessors() -> List[str]:
    """
    Liste tous les post-processeurs disponibles.
    
    Returns:
        Liste des noms des post-processeurs disponibles
    """
    return list(available_postprocessors.keys())

__all__ = [
    'JSONSimplifier',
    'get_postprocessor',
    'list_postprocessors',
    'available_postprocessors'
]