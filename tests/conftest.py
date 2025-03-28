"""
Configuration globale pour les tests pytest de l'API d'inférence multi-session.
"""

import pytest
import os
import requests
import time
import sys
from pathlib import Path

# Ajouter le répertoire racine du projet au PYTHONPATH
# Cette ligne résout le problème d'importation des modules
project_root = Path(__file__).parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"Ajout du chemin racine au sys.path: {project_root}")

# URL de base de l'API (ajuster selon l'environnement)
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Variables partagées entre les tests
shared_data = {
    "user": None,
    "token": None,
    "api_key": None
}

@pytest.fixture(scope="session", autouse=True)
def check_api_availability():
    """Vérifie si l'API est disponible avant d'exécuter les tests."""
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code != 200:
            pytest.skip(f"L'API n'est pas disponible ou a retourné un statut non-OK: {response.status_code}")
    except requests.exceptions.RequestException:
        pytest.skip("L'API n'est pas accessible")

@pytest.fixture(scope="session")
def api_url():
    """Retourne l'URL de base de l'API."""
    return BASE_URL

@pytest.fixture(scope="session")
def api_key():
    """Retourne une clé API valide pour les tests."""
    # Essayer d'utiliser une clé API fournie via variable d'environnement
    api_key = os.environ.get("TEST_API_KEY")
    if api_key:
        return api_key
    
    # Si aucune clé API n'est fournie, essayer de créer un utilisateur et une clé API
    if not shared_data["api_key"]:
        try:
            # Créer un utilisateur
            import random
            import string
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            username = f"testuser_{random_suffix}"
            
            user_data = {
                "username": username,
                "email": f"{username}@example.com",
                "password": "Password123!",
                "full_name": "Test User"
            }
            
            response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
            if response.status_code != 201:
                pytest.skip(f"Impossible de créer un utilisateur de test: {response.text}")
            
            user_info = response.json()
            shared_data["user"] = user_info
            
            # Se connecter pour obtenir un token
            login_data = {
                "username": username,
                "password": "Password123!"
            }
            
            response = requests.post(f"{BASE_URL}/auth/token", data=login_data)
            if response.status_code != 200:
                pytest.skip(f"Impossible d'obtenir un token: {response.text}")
            
            token_info = response.json()
            shared_data["token"] = token_info["access_token"]
            
            # Créer une clé API
            headers = {
                "Authorization": f"Bearer {shared_data['token']}"
            }
            
            key_data = {
                "name": "Test API Key"
            }
            
            response = requests.post(f"{BASE_URL}/auth/api-keys", json=key_data, headers=headers)
            if response.status_code != 201:
                pytest.skip(f"Impossible de créer une clé API: {response.text}")
            
            api_key_info = response.json()
            shared_data["api_key"] = api_key_info["key"]
            
        except Exception as e:
            pytest.skip(f"Erreur lors de la création d'une clé API de test: {e}")
    
    return shared_data["api_key"]

@pytest.fixture(scope="session")
def auth_headers(api_key):
    """Retourne les headers d'authentification avec une clé API."""
    return {
        "X-API-Key": api_key
    }

@pytest.fixture(scope="session")
def wait_for_completion():
    """Fonction utilitaire pour attendre la fin d'une tâche."""
    def _wait_for_completion(task_id, auth_headers, max_retries=30, interval=10):
        """Attend la fin d'une tâche et retourne son résultat."""
        for i in range(max_retries):
            response = requests.get(f"{BASE_URL}/api/inference/{task_id}", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            
            if data["status"] == "failed":
                pytest.fail(f"La tâche a échoué: {data.get('error', 'Erreur inconnue')}")
            
            if data["status"] == "completed":
                return data
                
            print(f"Attente de la fin de la tâche... Progression: {data.get('progress', 0):.0f}% (tentative {i+1}/{max_retries})")
                
            time.sleep(interval)
        
        pytest.fail(f"La tâche n'est pas terminée après {max_retries} tentatives")
    
    return _wait_for_completion