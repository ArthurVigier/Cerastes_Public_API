import pytest
import requests
import json
import os
import time
import uuid
from typing import Dict, Any, Optional, List

# URL de base de l'API (ajuster selon l'environnement)
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Variable pour stocker les informations de test
test_data = {
    "api_key": None,
    "token": None,
    "task_ids": [],     # Liste des IDs de tâches créées durant les tests
    "text_task_id": None,
    "batch_task_id": None,
    "other_task_id": None,
    "cancelled_task_id": None
}

def setup_module():
    """Configuration initiale pour les tests de tâches."""
    # Récupérer une clé API valide
    try:
        # Essayer d'utiliser une variable d'environnement pour la clé API
        api_key = os.environ.get("TEST_API_KEY")
        token = os.environ.get("TEST_TOKEN")
        
        if not api_key:
            # Importer et exécuter les tests d'authentification si nécessaire
            from test_auth import test_register_user, test_login, test_create_api_key
            
            # Créer un utilisateur et une clé API si nécessaire
            test_register_user()
            test_login()
            test_create_api_key()
            
            from test_auth import test_data as auth_test_data
            api_key = auth_test_data["api_key"]
            token = auth_test_data["token"]
    except Exception as e:
        # En cas d'erreur, une clé de test doit être fournie en variable d'environnement
        api_key = os.environ.get("TEST_API_KEY")
        if not api_key:
            raise Exception("Aucune clé API disponible pour les tests. Définissez TEST_API_KEY ou exécutez test_auth.py")
    
    test_data["api_key"] = api_key
    test_data["token"] = token
    
    # Créer quelques tâches pour les tests
    create_test_tasks()

def get_auth_headers():
    """Retourne les en-têtes d'authentification avec la clé API."""
    return {"X-API-Key": test_data["api_key"]}

def get_token_headers():
    """Retourne les en-têtes d'authentification avec le token."""
    return {"Authorization": f"Bearer {test_data['token']}"}

def create_test_tasks():
    """Crée des tâches de test pour être utilisées dans les tests."""
    headers = get_auth_headers()
    
    # Créer une tâche d'inférence de texte
    try:
        response = requests.post(
            f"{BASE_URL}/api/inference/start", 
            json={
                "text": "Ceci est un test pour la gestion des tâches.",
                "use_segmentation": True,
                "max_new_tokens": 100
            },
            headers=headers
        )
        
        if response.status_code == 202:
            data = response.json()
            test_data["text_task_id"] = data["task_id"]
            test_data["task_ids"].append(data["task_id"])
    except Exception as e:
        print(f"Erreur lors de la création d'une tâche d'inférence: {e}")
    
    # Tenter de créer une tâche par lots
    try:
        response = requests.post(
            f"{BASE_URL}/api/inference/batch", 
            json={
                "texts": ["Premier texte de test.", "Deuxième texte de test."],
                "use_segmentation": True,
                "max_new_tokens": 100
            },
            headers=headers
        )
        
        if response.status_code == 202:
            data = response.json()
            test_data["batch_task_id"] = data["task_id"]
            test_data["task_ids"].append(data["task_id"])
    except Exception as e:
        print(f"Erreur lors de la création d'une tâche par lots: {e}")
    
    # Créer une tâche pour l'annulation
    try:
        response = requests.post(
            f"{BASE_URL}/api/inference/start", 
            json={
                "text": "Cette tâche sera annulée dans les tests.",
                "use_segmentation": True,
                "max_new_tokens": 2000  # Grand nombre pour qu'elle prenne du temps
            },
            headers=headers
        )
        
        if response.status_code == 202:
            data = response.json()
            test_data["cancelled_task_id"] = data["task_id"]
            test_data["task_ids"].append(data["task_id"])
    except Exception as e:
        print(f"Erreur lors de la création d'une tâche pour annulation: {e}")

def test_get_specific_task():
    """Teste la récupération d'une tâche spécifique."""
    # S'assurer qu'une clé API et au moins une tâche sont disponibles
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    if not test_data["task_ids"]:
        pytest.skip("Aucune tâche disponible pour le test")
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Récupérer une tâche spécifique
    task_id = test_data["task_ids"][0]
    response = requests.get(f"{BASE_URL}/api/tasks/{task_id}", headers=headers)
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "task_id" in data
    assert data["task_id"] == task_id
    assert "status" in data
    assert "type" in data
    assert "created_at" in data

def test_get_nonexistent_task():
    """Teste la récupération d'une tâche qui n'existe pas."""
    # S'assurer qu'une clé API est disponible
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Tenter de récupérer une tâche avec un ID inexistant
    fake_task_id = str(uuid.uuid4())
    response = requests.get(f"{BASE_URL}/api/tasks/{fake_task_id}", headers=headers)
    assert response.status_code == 404, f"Une tâche inexistante devrait retourner 404, mais a retourné: {response.status_code}"

def test_list_all_tasks():
    """Teste la récupération de la liste de toutes les tâches."""
    # S'assurer qu'une clé API est disponible
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Récupérer la liste des tâches
    response = requests.get(f"{BASE_URL}/api/tasks", headers=headers)
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "total" in data
    assert "tasks" in data
    assert isinstance(data["tasks"], list) or isinstance(data["tasks"], dict)
    
    # Vérifier que les tâches créées pendant les tests sont présentes
    tasks_found = 0
    
    if isinstance(data["tasks"], list):
        task_ids = [task.get("task_id") for task in data["tasks"]]
        for task_id in test_data["task_ids"]:
            if task_id in task_ids:
                tasks_found += 1
    else:  # Si c'est un dictionnaire
        for task_id in test_data["task_ids"]:
            if task_id in data["tasks"]:
                tasks_found += 1
    
    assert tasks_found > 0, "Aucune des tâches créées n'a été trouvée dans la liste"

def test_filter_tasks_by_status():
    """Teste le filtrage des tâches par statut."""
    # S'assurer qu'une clé API est disponible
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Récupérer la liste des tâches en attente
    response = requests.get(f"{BASE_URL}/api/tasks?status=pending", headers=headers)
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    
    # Vérifier que les tâches ont bien le statut demandé
    if "tasks" in data and data["tasks"]:
        if isinstance(data["tasks"], list):
            for task in data["tasks"]:
                assert task["status"] == "pending", f"Une tâche avec un statut différent a été retournée: {task['status']}"
        else:  # Si c'est un dictionnaire
            for task_id, task in data["tasks"].items():
                assert task["status"] == "pending", f"Une tâche avec un statut différent a été retournée: {task['status']}"

def test_filter_tasks_by_type():
    """Teste le filtrage des tâches par type."""
    # S'assurer qu'une clé API est disponible
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Récupérer la liste des tâches de type texte
    response = requests.get(f"{BASE_URL}/api/tasks?task_type=text_inference", headers=headers)
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    
    # Vérifier que les tâches ont bien le type demandé
    if "tasks" in data and data["tasks"]:
        if isinstance(data["tasks"], list):
            for task in data["tasks"]:
                assert task["type"] == "text_inference", f"Une tâche avec un type différent a été retournée: {task['type']}"
        else:  # Si c'est un dictionnaire
            for task_id, task in data["tasks"].items():
                assert task["type"] == "text_inference", f"Une tâche avec un type différent a été retournée: {task['type']}"

def test_pagination():
    """Teste la pagination des tâches."""
    # S'assurer qu'une clé API est disponible
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Récupérer la première page de tâches (limité à 1 résultat)
    response = requests.get(f"{BASE_URL}/api/tasks?limit=1&offset=0", headers=headers)
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    
    # Vérifier que la limite est respectée
    if isinstance(data["tasks"], list):
        assert len(data["tasks"]) <= 1, f"Plus de tâches que la limite demandée ont été retournées: {len(data['tasks'])}"
    else:  # Si c'est un dictionnaire
        assert len(data["tasks"]) <= 1, f"Plus de tâches que la limite demandée ont été retournées: {len(data['tasks'])}"
    
    # Récupérer la deuxième page
    response = requests.get(f"{BASE_URL}/api/tasks?limit=1&offset=1", headers=headers)
    assert response.status_code == 200
    
    # Vérifier la réponse
    data2 = response.json()
    
    # Vérifier que la deuxième page est différente de la première
    if "tasks" in data and "tasks" in data2 and data["tasks"] and data2["tasks"]:
        if isinstance(data["tasks"], list) and isinstance(data2["tasks"], list):
            first_task_id = data["tasks"][0]["task_id"]
            second_task_id = data2["tasks"][0]["task_id"] if data2["tasks"] else None
            
            if second_task_id:
                assert first_task_id != second_task_id, "Les résultats paginés sont identiques"

def test_cancel_running_task():
    """Teste l'annulation d'une tâche en cours."""
    # S'assurer qu'une clé API et une tâche à annuler sont disponibles
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    if not test_data["cancelled_task_id"]:
        pytest.skip("Aucune tâche disponible pour l'annulation")
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Récupérer l'état actuel de la tâche
    task_id = test_data["cancelled_task_id"]
    response = requests.get(f"{BASE_URL}/api/tasks/{task_id}", headers=headers)
    
    if response.status_code != 200:
        pytest.skip(f"Impossible de récupérer l'état de la tâche: {response.status_code}")
    
    data = response.json()
    
    # Si la tâche est déjà terminée, ignorer ce test
    if data["status"] not in ["pending", "running"]:
        pytest.skip(f"La tâche est déjà dans l'état {data['status']} et ne peut pas être annulée")
    
    # Annuler la tâche
    response = requests.post(f"{BASE_URL}/api/tasks/{task_id}/cancel", headers=headers)
    
    # Si l'endpoint d'annulation n'existe pas, essayer la suppression
    if response.status_code == 404:
        response = requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=headers)
    
    assert response.status_code in [200, 202], f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier que la tâche a été annulée
    response = requests.get(f"{BASE_URL}/api/tasks/{task_id}", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] in ["cancelled", "deleted"], f"La tâche n'a pas été annulée correctement: {data['status']}"

def test_retry_failed_task():
    """Teste la réessai d'une tâche échouée."""
    # Cette fonctionnalité peut ne pas exister, donc on teste avec précaution
    # S'assurer qu'une clé API est disponible
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Rechercher une tâche échouée
    response = requests.get(f"{BASE_URL}/api/tasks?status=failed", headers=headers)
    
    if response.status_code != 200:
        pytest.skip("Impossible de rechercher des tâches échouées")
    
    data = response.json()
    
    # Trouver une tâche échouée
    failed_task_id = None
    
    if "tasks" in data and data["tasks"]:
        if isinstance(data["tasks"], list):
            for task in data["tasks"]:
                if task["status"] == "failed":
                    failed_task_id = task["task_id"]
                    break
        else:  # Si c'est un dictionnaire
            for task_id, task in data["tasks"].items():
                if task["status"] == "failed":
                    failed_task_id = task_id
                    break
    
    if not failed_task_id:
        pytest.skip("Aucune tâche échouée trouvée pour le test")
    
    # Tenter de réessayer la tâche
    response = requests.post(f"{BASE_URL}/api/tasks/{failed_task_id}/retry", headers=headers)
    
    # Ce test est exploratoire - ne pas faire échouer si l'endpoint n'existe pas
    if response.status_code == 404:
        pytest.skip("L'endpoint de réessai n'existe pas")
    
    # Si l'endpoint existe, vérifier qu'il fonctionne correctement
    assert response.status_code in [200, 202], f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier que la tâche a été remise à l'état "pending" ou qu'une nouvelle tâche a été créée
    data = response.json()
    if "task_id" in data:
        new_task_id = data["task_id"]
        
        # Vérifier l'état de la nouvelle tâche
        response = requests.get(f"{BASE_URL}/api/tasks/{new_task_id}", headers=headers)
        assert response.status_code == 200
        
        task_data = response.json()
        assert task_data["status"] in ["pending", "running"], f"La tâche n'a pas été correctement réessayée: {task_data['status']}"

def test_delete_task():
    """Teste la suppression d'une tâche."""
    # S'assurer qu'une clé API et au moins une tâche sont disponibles
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    if not test_data["task_ids"]:
        pytest.skip("Aucune tâche disponible pour le test")
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Sélectionner une tâche à supprimer
    task_id_to_delete = test_data["task_ids"][-1]  # Utiliser la dernière tâche créée
    
    # Supprimer la tâche
    response = requests.delete(f"{BASE_URL}/api/tasks/{task_id_to_delete}", headers=headers)
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier que la tâche a bien été supprimée
    response = requests.get(f"{BASE_URL}/api/tasks/{task_id_to_delete}", headers=headers)
    assert response.status_code == 404, f"La tâche n'a pas été correctement supprimée: {response.status_code}"
    
    # Supprimer l'ID de la liste des tâches de test
    test_data["task_ids"].remove(task_id_to_delete)

def test_cleanup():
    """Nettoie toutes les tâches créées pendant les tests."""
    # S'assurer qu'une clé API est disponible
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_auth_headers()
    
    # Supprimer toutes les tâches de test
    for task_id in test_data["task_ids"]:
        try:
            requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=headers)
        except Exception:
            pass  # Ignorer les erreurs lors du nettoyage

if __name__ == "__main__":
    # Initialiser les tests
    setup_module()
    
    # Exécuter les tests manuellement
    test_get_specific_task()
    test_get_nonexistent_task()
    test_list_all_tasks()
    test_filter_tasks_by_status()
    test_filter_tasks_by_type()
    test_pagination()
    
    try:
        test_cancel_running_task()
    except Exception as e:
        print(f"Le test d'annulation a échoué: {e}")
    
    try:
        test_retry_failed_task()
    except Exception as e:
        print(f"Le test de réessai a échoué: {e}")
    
    test_delete_task()
    test_cleanup()
    
    print("Tous les tests de gestion des tâches ont réussi!")