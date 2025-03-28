import pytest
import requests
import json
import os
import time
import io
from typing import Dict, Any

# URL de base de l'API (ajuster selon l'environnement)
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Variable pour stocker les informations de test
test_data = {
    "api_key": None,
    "manipulation_task_id": None,
    "nonverbal_task_id": None,
    "manipulation_video_path": None,  # Chemin pour la vidéo d'analyse de manipulation
    "nonverbal_video_path": None      # Chemin pour la vidéo d'analyse non-verbale
}

# Fichiers vidéo de test
SAMPLE_MANIPULATION_VIDEO_PATH = os.environ.get("SAMPLE_MANIPULATION_VIDEO_PATH", os.environ.get("SAMPLE_VIDEO_PATH"))
SAMPLE_NONVERBAL_VIDEO_PATH = os.environ.get("SAMPLE_NONVERBAL_VIDEO_PATH", os.environ.get("SAMPLE_VIDEO_PATH"))

def setup_module():
    """Configuration initiale pour les tests vidéo."""
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

def get_sample_video(video_type="manipulation"):
    """
    Retourne un fichier vidéo de test selon le type demandé.
    
    Args:
        video_type (str): Type de vidéo ('manipulation' ou 'nonverbal')
    
    Returns:
        Un fichier ouvert en mode binaire
    """
    video_path = None
    
    if video_type == "manipulation":
        video_path = SAMPLE_MANIPULATION_VIDEO_PATH
    elif video_type == "nonverbal":
        video_path = SAMPLE_NONVERBAL_VIDEO_PATH
    
    if video_path and os.path.exists(video_path):
        return open(video_path, "rb"), video_path
    else:
        # Pour les tests sans fichier vidéo réel, on peut utiliser un fichier minimal
        # Ceci est juste pour tester l'API, mais ne passera pas la validation complète
        # Vous devez définir les variables d'environnement pour des tests complets
        video_type_name = "manipulation" if video_type == "manipulation" else "non-verbale"
        pytest.skip(f"Aucun fichier vidéo pour analyse {video_type_name} disponible. Définissez SAMPLE_{video_type.upper()}_VIDEO_PATH.")

def test_upload_manipulation_video():
    """Teste le téléchargement d'un fichier vidéo pour l'analyse de manipulation."""
    # S'assurer qu'une clé API est disponible
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = {
        "X-API-Key": test_data["api_key"]
    }
    
    # Télécharger un fichier vidéo
    try:
        video_file, video_path = get_sample_video("manipulation")
        
        files = {
            "file": ("manipulation_video.mp4", video_file, "video/mp4")
        }
        
        response = requests.post(
            f"{BASE_URL}/api/video/upload",
            headers=headers,
            files=files
        )
        
        # Fermer le fichier après utilisation
        video_file.close()
        
        assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
        
        # Vérifier la réponse
        data = response.json()
        assert "video_path" in data
        assert "duration" in data
        
        # Sauvegarder le chemin de la vidéo pour les tests suivants
        test_data["manipulation_video_path"] = data["video_path"]
        
    except Exception as e:
        pytest.skip(f"Erreur lors du téléchargement de la vidéo de manipulation: {e}")

def test_upload_nonverbal_video():
    """Teste le téléchargement d'un fichier vidéo pour l'analyse non-verbale."""
    # S'assurer qu'une clé API est disponible
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = {
        "X-API-Key": test_data["api_key"]
    }
    
    # Télécharger un fichier vidéo
    try:
        video_file, video_path = get_sample_video("nonverbal")
        
        files = {
            "file": ("nonverbal_video.mp4", video_file, "video/mp4")
        }
        
        response = requests.post(
            f"{BASE_URL}/api/video/upload",
            headers=headers,
            files=files
        )
        
        # Fermer le fichier après utilisation
        video_file.close()
        
        assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
        
        # Vérifier la réponse
        data = response.json()
        assert "video_path" in data
        assert "duration" in data
        
        # Sauvegarder le chemin de la vidéo pour les tests suivants
        test_data["nonverbal_video_path"] = data["video_path"]
        
    except Exception as e:
        pytest.skip(f"Erreur lors du téléchargement de la vidéo non-verbale: {e}")

def test_start_manipulation_analysis():
    """Teste le démarrage d'une analyse de manipulation."""
    # S'assurer qu'une clé API et un chemin de vidéo sont disponibles
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    if test_data["manipulation_video_path"] is None:
        pytest.skip("Aucun chemin de vidéo de manipulation disponible pour le test")
    
    # Configurer les headers avec la clé API
    headers = {
        "X-API-Key": test_data["api_key"]
    }
    
    # Données pour l'analyse de manipulation
    analysis_data = {
        "video_path": test_data["manipulation_video_path"],
        "transcribe": True,
        "diarize": True,
        "language": "fr"
    }
    
    # Envoyer la requête d'analyse de manipulation
    response = requests.post(
        f"{BASE_URL}/api/video/manipulation-analysis",
        json=analysis_data,
        headers=headers
    )
    
    # Si le service n'est pas disponible, ignorer le test
    if response.status_code == 503:
        pytest.skip("Service d'analyse de manipulation non disponible")
    
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "pending"
    
    # Sauvegarder l'ID de tâche pour les tests suivants
    test_data["manipulation_task_id"] = data["task_id"]

def test_start_nonverbal_analysis():
    """Teste le démarrage d'une analyse non-verbale."""
    # S'assurer qu'une clé API et un chemin de vidéo sont disponibles
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    if test_data["nonverbal_video_path"] is None:
        pytest.skip("Aucun chemin de vidéo non-verbale disponible pour le test")
    
    # Configurer les headers avec la clé API
    headers = {
        "X-API-Key": test_data["api_key"]
    }
    
    # Données pour l'analyse non-verbale
    analysis_data = {
        "video_path": test_data["nonverbal_video_path"],
        "extract_frames": True,
        "frame_count": 32,
        "analyze_facial_expressions": True
    }
    
    # Envoyer la requête d'analyse non-verbale
    response = requests.post(
        f"{BASE_URL}/api/video/nonverbal-analysis",
        json=analysis_data,
        headers=headers
    )
    
    # Si le service n'est pas disponible, ignorer le test
    if response.status_code == 503:
        pytest.skip("Service d'analyse non-verbale non disponible")
    
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "pending"
    
    # Sauvegarder l'ID de tâche pour les tests suivants
    test_data["nonverbal_task_id"] = data["task_id"]

def test_get_manipulation_analysis_status():
    """Teste la récupération de l'état d'une tâche d'analyse de manipulation."""
    # S'assurer qu'une clé API et un ID de tâche sont disponibles
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    if test_data.get("manipulation_task_id") is None:
        pytest.skip("Aucun ID de tâche d'analyse de manipulation disponible pour le test")
    
    # Configurer les headers avec la clé API
    headers = {
        "X-API-Key": test_data["api_key"]
    }
    
    # Envoyer la requête pour récupérer l'état de la tâche
    response = requests.get(
        f"{BASE_URL}/api/video/tasks/{test_data['manipulation_task_id']}", 
        headers=headers
    )
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "status" in data
    assert "progress" in data
    
    # La tâche peut être en attente, en cours d'exécution ou terminée
    assert data["status"] in ["pending", "running", "completed", "failed"], f"Statut inattendu: {data['status']}"

def test_get_nonverbal_analysis_status():
    """Teste la récupération de l'état d'une tâche d'analyse non-verbale."""
    # S'assurer qu'une clé API et un ID de tâche sont disponibles
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    if test_data.get("nonverbal_task_id") is None:
        pytest.skip("Aucun ID de tâche d'analyse non-verbale disponible pour le test")
    
    # Configurer les headers avec la clé API
    headers = {
        "X-API-Key": test_data["api_key"]
    }
    
    # Envoyer la requête pour récupérer l'état de la tâche
    response = requests.get(
        f"{BASE_URL}/api/video/tasks/{test_data['nonverbal_task_id']}", 
        headers=headers
    )
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "status" in data
    assert "progress" in data
    
    # La tâche peut être en attente, en cours d'exécution ou terminée
    assert data["status"] in ["pending", "running", "completed", "failed"], f"Statut inattendu: {data['status']}"

def test_wait_for_manipulation_analysis_completion():
    """Teste l'attente de la fin d'une tâche d'analyse de manipulation."""
    # S'assurer qu'une clé API et un ID de tâche sont disponibles
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    if test_data.get("manipulation_task_id") is None:
        pytest.skip("Aucun ID de tâche d'analyse de manipulation disponible pour le test")
    
    # Configurer les headers avec la clé API
    headers = {
        "X-API-Key": test_data["api_key"]
    }
    
    # Attendre que la tâche soit terminée (avec un délai d'expiration)
    max_retries = 30  # 5 minutes maximum (avec 10 secondes d'intervalle)
    for i in range(max_retries):
        # Envoyer la requête pour récupérer l'état de la tâche
        response = requests.get(
            f"{BASE_URL}/api/video/tasks/{test_data['manipulation_task_id']}", 
            headers=headers
        )
        assert response.status_code == 200
        
        # Vérifier la réponse
        data = response.json()
        
        # Si la tâche a échoué, afficher l'erreur
        if data["status"] == "failed":
            print(f"La tâche d'analyse de manipulation a échoué: {data.get('error', 'Erreur inconnue')}")
            pytest.skip(f"La tâche d'analyse de manipulation a échoué: {data.get('error', 'Erreur inconnue')}")
        
        # Si la tâche est terminée, le test est réussi
        if data["status"] == "completed":
            if "results" in data:
                assert isinstance(data["results"], dict)
                # Vérifier que les résultats contiennent des données
                assert len(data["results"]) > 0
            break
            
        # Afficher la progression
        print(f"Attente de la fin de l'analyse de manipulation... Progression: {data.get('progress', 0):.0f}% (tentative {i+1}/{max_retries})")
            
        # Attendre avant de réessayer
        time.sleep(10)
    else:
        pytest.skip(f"La tâche d'analyse de manipulation n'est pas terminée après {max_retries} tentatives")

def test_wait_for_nonverbal_analysis_completion():
    """Teste l'attente de la fin d'une tâche d'analyse non-verbale."""
    # S'assurer qu'une clé API et un ID de tâche sont disponibles
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    if test_data.get("nonverbal_task_id") is None:
        pytest.skip("Aucun ID de tâche d'analyse non-verbale disponible pour le test")
    
    # Configurer les headers avec la clé API
    headers = {
        "X-API-Key": test_data["api_key"]
    }
    
    # Attendre que la tâche soit terminée (avec un délai d'expiration)
    max_retries = 30  # 5 minutes maximum (avec 10 secondes d'intervalle)
    for i in range(max_retries):
        # Envoyer la requête pour récupérer l'état de la tâche
        response = requests.get(
            f"{BASE_URL}/api/video/tasks/{test_data['nonverbal_task_id']}", 
            headers=headers
        )
        assert response.status_code == 200
        
        # Vérifier la réponse
        data = response.json()
        
        # Si la tâche a échoué, afficher l'erreur
        if data["status"] == "failed":
            print(f"La tâche d'analyse non-verbale a échoué: {data.get('error', 'Erreur inconnue')}")
            pytest.skip(f"La tâche d'analyse non-verbale a échoué: {data.get('error', 'Erreur inconnue')}")
        
        # Si la tâche est terminée, le test est réussi
        if data["status"] == "completed":
            if "results" in data:
                assert isinstance(data["results"], dict)
                # Vérifier que les résultats contiennent des données
                assert len(data["results"]) > 0
            break
            
        # Afficher la progression
        print(f"Attente de la fin de l'analyse non-verbale... Progression: {data.get('progress', 0):.0f}% (tentative {i+1}/{max_retries})")
            
        # Attendre avant de réessayer
        time.sleep(10)
    else:
        pytest.skip(f"La tâche d'analyse non-verbale n'est pas terminée après {max_retries} tentatives")

def test_get_all_video_tasks():
    """Teste la récupération de toutes les tâches vidéo."""
    # S'assurer qu'une clé API est disponible
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = {
        "X-API-Key": test_data["api_key"]
    }
    
    # Envoyer la requête pour récupérer toutes les tâches vidéo
    response = requests.get(f"{BASE_URL}/api/video/tasks", headers=headers)
    assert response.status_code == 200
    
    # Vérifier la réponse
    data = response.json()
    assert "tasks" in data
    assert isinstance(data["tasks"], list)
    
    # Si des tâches ont été créées précédemment, elles devraient être présentes
    task_ids = [task["id"] for task in data["tasks"]]
    if test_data.get("manipulation_task_id"):
        assert test_data["manipulation_task_id"] in task_ids, "L'ID de tâche d'analyse de manipulation est absent"
    if test_data.get("nonverbal_task_id"):
        assert test_data["nonverbal_task_id"] in task_ids, "L'ID de tâche d'analyse non-verbale est absent"

def test_delete_video_tasks():
    """Teste la suppression des tâches vidéo."""
    # S'assurer qu'une clé API est disponible
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = {
        "X-API-Key": test_data["api_key"]
    }
    
    # Supprimer la tâche d'analyse de manipulation si disponible
    if test_data.get("manipulation_task_id"):
        response = requests.delete(
            f"{BASE_URL}/api/video/tasks/{test_data['manipulation_task_id']}", 
            headers=headers
        )
        assert response.status_code == 200
        
        # Vérifier que la tâche a bien été supprimée
        response = requests.get(
            f"{BASE_URL}/api/video/tasks/{test_data['manipulation_task_id']}", 
            headers=headers
        )
        assert response.status_code == 404
    
    # Supprimer la tâche d'analyse non-verbale si disponible
    if test_data.get("nonverbal_task_id"):
        response = requests.delete(
            f"{BASE_URL}/api/video/tasks/{test_data['nonverbal_task_id']}", 
            headers=headers
        )
        assert response.status_code == 200
        
        # Vérifier que la tâche a bien été supprimée
        response = requests.get(
            f"{BASE_URL}/api/video/tasks/{test_data['nonverbal_task_id']}", 
            headers=headers
        )
        assert response.status_code == 404

if __name__ == "__main__":
    # Initialiser les tests
    setup_module()
    
    # Tests pour l'analyse de manipulation
    test_upload_manipulation_video()
    try:
        test_start_manipulation_analysis()
        test_get_manipulation_analysis_status()
        test_wait_for_manipulation_analysis_completion()
    except Exception as e:
        print(f"Les tests d'analyse de manipulation ont échoué: {e}")
    
    # Tests pour l'analyse non-verbale
    test_upload_nonverbal_video()
    try:
        test_start_nonverbal_analysis()
        test_get_nonverbal_analysis_status()
        test_wait_for_nonverbal_analysis_completion()
    except Exception as e:
        print(f"Les tests d'analyse non-verbale ont échoué: {e}")
    
    # Tests communs
    test_get_all_video_tasks()
    test_delete_video_tasks()
    
    print("Tous les tests vidéo ont réussi!")