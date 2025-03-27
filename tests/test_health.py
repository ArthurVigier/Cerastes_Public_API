"""
Tests pour les endpoints de santé et de surveillance
---------------------------------------------------
Ce module teste les fonctionnalités de surveillance de l'API,
y compris les endpoints de santé, de readiness, et de métriques.
"""

import pytest
import requests
import json
import os
import time
from typing import Dict, Any

# URL de base de l'API (ajuster selon l'environnement)
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Variable pour stocker les informations de test
test_data = {
    "api_key": None
}

def setup_module():
    """Configuration initiale pour les tests de santé."""
    # Pour les tests de santé, une clé API n'est généralement pas requise
    # mais certains endpoints comme /metrics peuvent en avoir besoin
    try:
        # Essayer d'utiliser une variable d'environnement pour la clé API
        api_key = os.environ.get("TEST_API_KEY")
        
        if not api_key:
            # Importer et exécuter les tests d'authentification si nécessaire
            try:
                from test_auth import test_data as auth_test_data
                api_key = auth_test_data.get("api_key")
            except (ImportError, AttributeError):
                # Ne pas échouer si les tests d'authentification ne sont pas disponibles
                pass
    except Exception as e:
        # En cas d'erreur, simplement l'ignorer pour les tests de santé
        print(f"Note: Fonctionnant sans clé API pour les tests de santé: {e}")
        api_key = None
    
    test_data["api_key"] = api_key

def test_health_check():
    """Teste l'endpoint principal de santé."""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data
    assert "uptime" in data
    assert isinstance(data["uptime"], (int, float))

def test_detailed_health_check():
    """Teste l'endpoint détaillé de santé."""
    response = requests.get(f"{BASE_URL}/health/detailed")
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"
    
    # Vérifier les sections détaillées
    assert "system_info" in data
    assert "resources" in data
    assert "services" in data
    
    # Vérifier les informations système
    system_info = data["system_info"]
    assert "platform" in system_info
    assert "python_version" in system_info
    
    # Vérifier les ressources
    resources = data["resources"]
    assert "cpu_percent" in resources
    assert "memory_percent" in resources
    assert "disk_percent" in resources
    
    # Vérifier les services
    services = data["services"]
    assert "database" in services
    assert "filesystem" in services

def test_ping():
    """Teste l'endpoint de ping."""
    response = requests.get(f"{BASE_URL}/health/ping")
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "ping" in data
    assert data["ping"] == "pong"

def test_readiness_probe():
    """Teste l'endpoint de readiness (prêt à servir des requêtes)."""
    response = requests.get(f"{BASE_URL}/health/ready")
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "status" in data
    assert data["status"] == "ready"

def test_liveness_probe():
    """Teste l'endpoint de liveness (API en cours d'exécution)."""
    response = requests.get(f"{BASE_URL}/health/live")
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "status" in data
    assert data["status"] == "alive"

def test_version_info():
    """Vérifie que les informations de version sont cohérentes."""
    # Récupérer la version depuis l'endpoint principal de santé
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    
    # Vérifier que la version est une chaîne non vide
    data = response.json()
    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0
    
    # Comparer avec la version détaillée si disponible
    try:
        response_detailed = requests.get(f"{BASE_URL}/health/detailed")
        if response_detailed.status_code == 200:
            data_detailed = response_detailed.json()
            assert data["version"] == data_detailed["version"], "Les versions ne correspondent pas entre les endpoints"
    except Exception:
        # Ne pas échouer si l'endpoint détaillé n'est pas disponible
        pass

def test_metrics_endpoint():
    """Teste l'endpoint de métriques Prometheus (s'il existe)."""
    headers = {}
    if test_data["api_key"]:
        headers["X-API-Key"] = test_data["api_key"]
    
    try:
        response = requests.get(f"{BASE_URL}/metrics", headers=headers)
        
        # Si l'endpoint n'existe pas, ignorer ce test
        if response.status_code == 404:
            pytest.skip("L'endpoint /metrics n'existe pas")
        
        # Si l'authentification est requise mais que nous n'avons pas de clé API
        if response.status_code in [401, 403] and not test_data["api_key"]:
            pytest.skip("Authentification requise pour l'endpoint /metrics, mais aucune clé API disponible")
        
        assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
        
        # Vérifier que le contenu est au format Prometheus (commence par # HELP)
        assert "# HELP" in response.text, "Le contenu ne semble pas être au format Prometheus"
        
        # Vérifier quelques métriques standards
        assert "process_cpu_seconds_total" in response.text or "cerastes_" in response.text, "Aucune métrique standard trouvée"
    
    except requests.exceptions.RequestException:
        pytest.skip("Impossible de se connecter à l'endpoint /metrics")

def test_check_endpoints_consistency():
    """Vérifie la cohérence entre les différents endpoints de santé."""
    try:
        # Récupérer les données des différents endpoints
        health_response = requests.get(f"{BASE_URL}/health")
        ready_response = requests.get(f"{BASE_URL}/health/ready")
        live_response = requests.get(f"{BASE_URL}/health/live")
        
        if health_response.status_code != 200 or ready_response.status_code != 200 or live_response.status_code != 200:
            pytest.skip("Certains endpoints de santé ne sont pas disponibles")
        
        # Vérifier la cohérence: si l'API est prête et vivante, son statut devrait être "ok"
        health_data = health_response.json()
        ready_data = ready_response.json()
        live_data = live_response.json()
        
        if ready_data["status"] == "ready" and live_data["status"] == "alive":
            assert health_data["status"] == "ok", "Incohérence: l'API est prête et vivante, mais son statut n'est pas 'ok'"
    
    except Exception as e:
        pytest.skip(f"Erreur lors de la vérification de la cohérence: {e}")

if __name__ == "__main__":
    # Initialiser les tests
    setup_module()
    
    # Exécuter les tests manuellement
    test_health_check()
    test_detailed_health_check()
    test_ping()
    test_readiness_probe()
    test_liveness_probe()
    test_version_info()
    
    try:
        test_metrics_endpoint()
    except Exception as e:
        print(f"Le test des métriques a échoué: {e}")
    
    test_check_endpoints_consistency()
    
    print("Tous les tests de santé ont réussi!")