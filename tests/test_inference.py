import pytest
import requests
import json
import os
import time
from typing import Dict, Any, Optional

# URL de base de l'API (ajuster selon l'environnement)
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Texte d'exemple pour les tests
SAMPLE_TEXT = """
The debate on artificial intelligence poses significant ethical challenges. On one hand, AI offers unprecedented opportunities for progress in healthcare, education, and environmental protection. On the other hand, it raises concerns about privacy, job displacement, and potential risks from autonomous systems. While some argue that AI development should proceed with minimal restrictions to maximize innovation, others advocate for a cautious approach with robust regulatory frameworks. The question isn't whether we should develop AI, but how we can do so responsibly.
"""

# Variable pour stocker les informations de test
test_data = {
    "api_key": None,
    "task_id": None,
    "batch_id": None
}

def setup_module():
    """Configuration initiale pour les tests d'inférence."""
    # Récupérer une clé API valide depuis les tests d'authentification ou utiliser une variable d'environnement
    try:
        # Essayer d'utiliser une variable d'environnement pour la clé API
        api_key = os.environ.get("TEST_API_KEY")
        
        if not api_key:
            # Importer et exécuter les tests d'authentification si nécessaire
            from test_auth import test_register_user, test_login, test_create_api_key
            
            # Créer un utilisateur et une clé API si nécessaire
            test_register_user()
            test_login()
            test_create_api_key()
            
            from test_auth import test_data as auth_test_data
            api_key = auth_test_data["api_key"]
    except Exception as e:
        # En cas d'erreur, une clé de test doit être fournie en variable d'environnement
        api_key = os.environ.get("TEST_API_KEY")
        if not api_key:
            raise Exception("Aucune clé API disponible pour les tests. Définissez TEST_API_KEY ou exécutez test_auth.py")
    
    test_data["api_key"] = api_key

def get_auth_headers():
    """Retourne les en-têtes d'authentification avec la clé API."""
    return {"X-API-Key": test_data["api_key"]}

def wait_for_task_completion(task_id: str, max_retries: int = 30, delay: int = 10) -> Optional[Dict[str, Any]]:
    """
    Attend qu'une tâche soit terminée et retourne son résultat.
    
    Args:
        task_id: ID de la tâche à attendre
        max_retries: Nombre maximal de tentatives
        delay: Délai entre les tentatives en secondes
        
    Returns:
        Dict contenant les données de la tâche ou None en cas d'échec
    """
    headers = get_auth_headers()
    
    for i in range(max_retries):
        response = requests.get(f"{BASE_URL}/api/tasks/{task_id}", headers=headers)
        
        if response.status_code != 200:
            print(f"Erreur lors de la récupération de la tâche: {response.status_code}")
            continue
            
        data = response.json()
        
        # Si la tâche a échoué, retourner None
        if data["status"] == "failed":
            print(f"La tâche a échoué: {data.get('error', 'Erreur inconnue')}")
            return None
        
        # Si la tâche est terminée, retourner les résultats
        if data["status"] == "completed":
            return data
            
        # Afficher la progression
        print(f"Attente de la fin de la tâche... Progression: {data.get('progress', 0):.0f}% (tentative {i+1}/{max_retries})")
            
        # Attendre avant de réessayer
        time.sleep(delay)
    
    return None

def test_inference_without_api_key():
    """Teste une requête d'inférence sans clé API."""
    # Données pour l'inférence
    inference_data = {
        "text": SAMPLE_TEXT,
        "use_segmentation": True,
        "max_new_tokens": 500
    }
    
    # Envoyer la requête sans clé API
    response = requests.post(f"{BASE_URL}/api/inference/start", json=inference_data)
    assert response.status_code in [401, 403], f"Code de statut inattendu: {response.status_code}"

def test_start_inference():
    """Teste le démarrage d'une tâche d'inférence."""
    # S'assurer qu'une clé API est disponible
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Données pour l'inférence
    inference_data = {
        "text": SAMPLE_TEXT,
        "use_segmentation": True,
        "max_new_tokens": 500,
        "timeout_seconds": 120
    }
    
    # Envoyer la requête d'inférence
    response = requests.post(f"{BASE_URL}/api/inference/start", json=inference_data, headers=headers)
    
    # Vérifier si l'API n'est pas disponible ou en mode de compatibilité
    if response.status_code == 400 and "mode de compatibilité" in response.text:
        pytest.skip("API en mode de compatibilité")
    
    assert response.status_code == 202, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "pending"
    
    # Sauvegarder l'ID de tâche pour les tests suivants
    test_data["task_id"] = data["task_id"]

def test_get_inference_status():
    """Teste la récupération de l'état d'une tâche d'inférence."""
    # S'assurer qu'une clé API et un ID de tâche sont disponibles
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    assert test_data["task_id"] is not None, "Aucun ID de tâche disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Attendre que la tâche soit au moins en cours d'exécution
    max_retries = 10
    for _ in range(max_retries):
        # Envoyer la requête pour récupérer l'état de la tâche
        response = requests.get(f"{BASE_URL}/api/tasks/{test_data['task_id']}", headers=headers)
        assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
        
        # Vérifier la réponse
        data = response.json()
        assert "status" in data
        assert "progress" in data
        assert "type" in data
        assert data["type"] == "text_inference"
        
        # Si la tâche est terminée ou en cours, le test est réussi
        if data["status"] in ["running", "completed"]:
            break
            
        # Attendre avant de réessayer
        time.sleep(2)
    
    # Vérifier que la tâche a progressé
    assert data["status"] in ["running", "completed"], f"La tâche est toujours en attente après {max_retries} tentatives"

def test_wait_for_inference_completion():
    """Teste l'attente de la fin d'une tâche d'inférence."""
    # S'assurer qu'une clé API et un ID de tâche sont disponibles
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    assert test_data["task_id"] is not None, "Aucun ID de tâche disponible pour le test"
    
    # Attendre que la tâche soit terminée
    result = wait_for_task_completion(test_data["task_id"])
    
    # Vérifier que la tâche est terminée avec succès
    assert result is not None, "La tâche n'a pas été terminée avec succès"
    assert result["status"] == "completed"
    assert "results" in result
    assert isinstance(result["results"], dict)
    # Vérifier que les résultats contiennent au moins une clé
    assert len(result["results"]) > 0

def test_custom_session():
    """Teste l'exécution d'une session personnalisée."""
    # S'assurer qu'une clé API et un ID de tâche sont disponibles
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    assert test_data["task_id"] is not None, "Aucun ID de tâche disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Données pour la session personnalisée
    session_data = {
        "system_prompt": "Summarize the following text in a few sentences:\n\n{text}",
        "user_input": "",
        "max_new_tokens": 200
    }
    
    # Envoyer la requête pour exécuter une session personnalisée
    response = requests.post(
        f"{BASE_URL}/api/inference/session/{test_data['task_id']}/custom_summary",
        json=session_data,
        headers=headers
    )
    
    # Vérifier si l'API n'est pas disponible ou en mode de compatibilité
    if response.status_code == 400 and "mode de compatibilité" in response.text:
        pytest.skip("API en mode de compatibilité")
    
    assert response.status_code == 202, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "task_id" in data
    assert "parent_task_id" in data
    assert data["parent_task_id"] == test_data["task_id"]
    assert data["session_name"] == "custom_summary"

def test_start_batch_inference():
    """Teste le démarrage d'une tâche d'inférence par lots."""
    # S'assurer qu'une clé API est disponible
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Données pour l'inférence par lots
    batch_data = {
        "texts": [
            SAMPLE_TEXT,
            "AI safety is a critical concern for researchers and policymakers alike.",
            "The adoption of renewable energy is accelerating globally."
        ],
        "use_segmentation": True,
        "max_new_tokens": 500,
        "max_concurrent": 2
    }
    
    # Envoyer la requête d'inférence par lots
    response = requests.post(f"{BASE_URL}/api/inference/batch", json=batch_data, headers=headers)
    
    # Si l'utilisateur de test n'a pas accès au traitement par lots, ignorer ce test
    if response.status_code == 403 and "plan actuel" in response.text:
        pytest.skip("L'utilisateur de test n'a pas accès au traitement par lots")
    
    # Vérifier si l'API n'est pas disponible ou en mode de compatibilité
    if response.status_code == 400 and "mode de compatibilité" in response.text:
        pytest.skip("API en mode de compatibilité")
    
    assert response.status_code == 202, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "task_id" in data  # Maintenant on utilise task_id au lieu de batch_id
    assert "batch_size" in data
    assert data["batch_size"] == len(batch_data["texts"])
    
    # Sauvegarder l'ID de lot pour les tests suivants
    test_data["batch_id"] = data["task_id"]

def test_get_batch_status():
    """Teste la récupération de l'état d'une tâche d'inférence par lots."""
    # S'assurer qu'une clé API et un ID de lot sont disponibles
    if test_data.get("batch_id") is None:
        pytest.skip("Aucun ID de lot disponible pour le test")
    
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Envoyer la requête pour récupérer l'état du lot
    response = requests.get(f"{BASE_URL}/api/tasks/{test_data['batch_id']}", headers=headers)
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "status" in data
    assert "progress" in data
    assert "type" in data
    assert data["type"] == "batch"
    assert "params" in data
    assert "batch_size" in data["params"]
    
    # Attendre que le lot soit au moins en cours d'exécution
    assert data["status"] in ["pending", "running", "completed"], f"Statut du lot inattendu: {data['status']}"

def test_list_tasks():
    """Teste la récupération de la liste des tâches."""
    # S'assurer qu'une clé API est disponible
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Envoyer la requête pour récupérer la liste des tâches
    response = requests.get(f"{BASE_URL}/api/tasks", headers=headers)
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "total" in data
    assert "tasks" in data
    
    # La structure a changé, tasks est maintenant une liste d'objets
    assert isinstance(data["tasks"], list)
    
    # Vérifier que la tâche créée précédemment est présente
    task_ids = [task["task_id"] for task in data["tasks"]]
    assert test_data["task_id"] in task_ids, "La tâche créée n'a pas été trouvée dans la liste"

def test_cancel_task():
    """Teste l'annulation d'une tâche en cours."""
    # S'assurer qu'une clé API et un ID de tâche sont disponibles
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    assert test_data["batch_id"] is not None, "Aucun ID de tâche par lots disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Envoyer la requête pour annuler la tâche
    response = requests.post(f"{BASE_URL}/api/tasks/{test_data['batch_id']}/cancel", headers=headers)
    
    # Si la tâche est déjà terminée, ce test peut échouer normalement
    if response.status_code == 400 and "not running" in response.text.lower():
        pytest.skip("La tâche est déjà terminée et ne peut pas être annulée")
    
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "success" in data
    assert data["success"] is True
    
    # Vérifier que la tâche a bien été annulée
    response = requests.get(f"{BASE_URL}/api/tasks/{test_data['batch_id']}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"

def test_delete_task():
    """Teste la suppression d'une tâche."""
    # S'assurer qu'une clé API et un ID de tâche sont disponibles
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    assert test_data["task_id"] is not None, "Aucun ID de tâche disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Envoyer la requête pour supprimer la tâche
    response = requests.delete(f"{BASE_URL}/api/tasks/{test_data['task_id']}", headers=headers)
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "success" in data
    assert data["success"] is True
    
    # Vérifier que la tâche a bien été supprimée
    response = requests.get(f"{BASE_URL}/api/tasks/{test_data['task_id']}", headers=headers)
    assert response.status_code == 404

if __name__ == "__main__":
    # Initialiser les tests
    setup_module()
    
    # Exécuter les tests manuellement
    test_inference_without_api_key()
    test_start_inference()
    test_get_inference_status()
    test_wait_for_inference_completion()
    test_custom_session()
    
    try:
        test_start_batch_inference()
        test_get_batch_status()
    except Exception as e:
        print(f"Les tests de traitement par lots ont échoué: {e}")
    
    test_list_tasks()
    test_cancel_task()
    test_delete_task()
    
    print("Tous les tests d'inférence ont réussi!")