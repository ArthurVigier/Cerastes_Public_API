"""
Tests pour les fonctionnalités de transcription
----------------------------------------------
Ce module contient des tests pour les endpoints de transcription audio,
couvrant les fonctionnalités de monologue et multi-locuteurs.
"""

import os
import pytest
import json
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil

# Import de l'application principale
from main import app
from auth import create_access_token
from db.models import User

# Client de test
client = TestClient(app)

# Constantes pour les tests
TEST_AUDIO_PATH = Path(__file__).parent / "fixtures" / "test_audio.mp3"
TEST_USER_ID = "test_user"

# Créer le dossier fixtures s'il n'existe pas
if not (Path(__file__).parent / "fixtures").exists():
    os.makedirs(Path(__file__).parent / "fixtures")
    
# Créer un fichier audio de test s'il n'existe pas
if not TEST_AUDIO_PATH.exists():
    # Génération d'un fichier audio vide pour les tests
    with open(TEST_AUDIO_PATH, "wb") as f:
        # Créer un fichier MP3 minimal valide pour les tests
        # MP3 header minimal
        f.write(b'\xFF\xFB\x90\x44\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        # Ajouter des données supplémentaires pour simuler un fichier audio
        f.write(b'\x00' * 1024)


@pytest.fixture
def auth_headers():
    """Génère un token d'authentification pour les tests"""
    token = create_access_token(data={"sub": TEST_USER_ID})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_db_user():
    """Mock un utilisateur dans la base de données pour les tests"""
    with patch("auth.get_user_by_username") as mock_get_user:
        user = MagicMock()
        user.username = TEST_USER_ID
        user.is_active = True
        user.subscription_tier = "premium"  # Pour des tests sans limitation
        mock_get_user.return_value = user
        yield user


@pytest.fixture
def temp_upload_dir():
    """Crée un répertoire temporaire pour les uploads de test"""
    temp_dir = tempfile.mkdtemp()
    original_upload_dir = os.environ.get("UPLOAD_DIR")
    os.environ["UPLOAD_DIR"] = temp_dir
    yield temp_dir
    if original_upload_dir:
        os.environ["UPLOAD_DIR"] = original_upload_dir
    else:
        os.environ.pop("UPLOAD_DIR", None)
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_upload_audio_file(auth_headers, mock_db_user, temp_upload_dir):
    """Teste l'upload d'un fichier audio"""
    with open(TEST_AUDIO_PATH, "rb") as f:
        files = {"audio": ("test_audio.mp3", f, "audio/mpeg")}
        response = client.post(
            "/transcription/upload", 
            files=files,
            headers=auth_headers
        )
    
    assert response.status_code == 200
    result = response.json()
    assert "file_path" in result
    assert os.path.exists(result["file_path"])
    
    # Vérifier que le fichier a été correctement sauvegardé
    assert Path(result["file_path"]).stat().st_size > 0


@pytest.fixture
def mock_transcription_task():
    """Mock la création et mise à jour de tâche de transcription"""
    with patch("inference_engine.create_task") as mock_create:
        mock_create.return_value = "mock-task-id-123"
        with patch("inference_engine.update_task") as mock_update:
            mock_update.return_value = True
            yield mock_create, mock_update


def test_start_transcription_monologue(auth_headers, mock_db_user, mock_transcription_task):
    """Teste le démarrage d'une tâche de transcription monologue"""
    mock_create, mock_update = mock_transcription_task
    
    # Mock le processus d'upload pour éviter de manipuler des fichiers réels
    with patch("api.transcription_router.save_uploaded_file") as mock_save:
        mock_save.return_value = str(TEST_AUDIO_PATH)
        
        with open(TEST_AUDIO_PATH, "rb") as f:
            files = {"audio": ("test_audio.mp3", f, "audio/mpeg")}
            response = client.post(
                "/transcription/monologue", 
                files=files,
                data={"language": "fr", "model": "medium"},
                headers=auth_headers
            )
    
    assert response.status_code == 202
    result = response.json()
    assert "task_id" in result
    assert result["task_id"] == "mock-task-id-123"
    assert result["status"] == "pending"
    
    # Vérifier que la tâche a été créée correctement
    mock_create.assert_called_once()
    # Vérifier que le fichier a été traité
    mock_save.assert_called_once()


def test_start_transcription_multispeaker(auth_headers, mock_db_user, mock_transcription_task):
    """Teste le démarrage d'une tâche de transcription multi-locuteurs"""
    mock_create, mock_update = mock_transcription_task
    
    # Mock le processus d'upload pour éviter de manipuler des fichiers réels
    with patch("api.transcription_router.save_uploaded_file") as mock_save:
        mock_save.return_value = str(TEST_AUDIO_PATH)
        
        with open(TEST_AUDIO_PATH, "rb") as f:
            files = {"audio": ("test_audio.mp3", f, "audio/mpeg")}
            response = client.post(
                "/transcription/multispeaker", 
                files=files,
                data={
                    "language": "fr", 
                    "model": "medium",
                    "min_speakers": 2,
                    "max_speakers": 5
                },
                headers=auth_headers
            )
    
    assert response.status_code == 202
    result = response.json()
    assert "task_id" in result
    assert result["task_id"] == "mock-task-id-123"
    assert result["status"] == "pending"
    
    # Vérifier que les paramètres de diarisation sont passés correctement
    create_args = mock_create.call_args[1]
    assert "params" in create_args
    assert "min_speakers" in create_args["params"]
    assert create_args["params"]["min_speakers"] == 2


@patch("inference_engine.get_task_status")
def test_get_transcription_status(mock_get_status, auth_headers, mock_db_user):
    """Teste la récupération du statut d'une tâche de transcription"""
    # Simulation d'une tâche en cours
    mock_get_status.return_value = {
        "task_id": "mock-task-id-123",
        "status": "running",
        "progress": 0.45,
        "message": "Transcription en cours...",
        "created_at": time.time()
    }
    
    response = client.get(
        "/transcription/tasks/mock-task-id-123",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "running"
    assert "progress" in result
    assert result["progress"] == 0.45


@patch("inference_engine.get_task_status")
def test_wait_for_transcription_completion(mock_get_status, auth_headers, mock_db_user):
    """Teste l'attente de la fin d'une tâche de transcription"""
    # Simuler une tâche terminée
    mock_get_status.return_value = {
        "task_id": "mock-task-id-123",
        "status": "completed",
        "progress": 1.0,
        "message": "Transcription terminée avec succès",
        "created_at": time.time() - 10,  # Créée il y a 10 secondes
        "completed_at": time.time(),
        "results": {
            "transcription": "Ceci est un exemple de transcription de test.",
            "confidence": 0.92,
            "language": "fr",
            "duration": 5.2
        }
    }
    
    response = client.get(
        "/transcription/tasks/mock-task-id-123",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert "results" in result
    assert "transcription" in result["results"]
    assert result["results"]["language"] == "fr"


@patch("inference_engine.get_task_status")
def test_transcription_with_diarization(mock_get_status, auth_headers, mock_db_user):
    """Teste la récupération d'une transcription avec diarisation"""
    # Simuler une tâche de diarisation terminée
    mock_get_status.return_value = {
        "task_id": "mock-task-id-123",
        "status": "completed",
        "progress": 1.0,
        "message": "Transcription avec diarisation terminée",
        "created_at": time.time() - 15,
        "completed_at": time.time(),
        "results": {
            "transcription": [
                {"speaker": "SPEAKER_1", "text": "Bonjour, comment allez-vous?", "start": 0.0, "end": 2.5},
                {"speaker": "SPEAKER_2", "text": "Très bien, merci.", "start": 3.0, "end": 4.5},
                {"speaker": "SPEAKER_1", "text": "C'est une belle journée aujourd'hui.", "start": 5.0, "end": 7.5}
            ],
            "speakers": 2,
            "language": "fr",
            "duration": 8.0
        }
    }
    
    response = client.get(
        "/transcription/tasks/mock-task-id-123",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert "results" in result
    
    # Vérifier la structure des résultats de diarisation
    transcription = result["results"]["transcription"]
    assert isinstance(transcription, list)
    assert len(transcription) == 3
    assert transcription[0]["speaker"] == "SPEAKER_1"
    assert "start" in transcription[0]
    assert "end" in transcription[0]


def test_list_transcription_tasks(auth_headers, mock_db_user):
    """Teste la récupération de la liste des tâches de transcription"""
    # Mock la récupération des tâches
    with patch("inference_engine.list_tasks") as mock_list:
        mock_list.return_value = [
            {
                "task_id": "task-1",
                "type": "transcription_monologue",
                "status": "completed",
                "created_at": time.time() - 3600,
                "completed_at": time.time() - 3500
            },
            {
                "task_id": "task-2",
                "type": "transcription_multispeaker",
                "status": "running",
                "created_at": time.time() - 600
            }
        ]
        
        response = client.get(
            "/transcription/tasks",
            headers=auth_headers
        )
    
    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["task_id"] == "task-1"
    assert result[0]["type"] == "transcription_monologue"
    assert result[1]["status"] == "running"


@patch("api.transcription_router.process_audio_task")
def test_cancel_transcription_task(mock_process, auth_headers, mock_db_user):
    """Teste l'annulation d'une tâche de transcription"""
    # Mocke la mise à jour du statut
    with patch("inference_engine.update_task_status") as mock_update:
        mock_update.return_value = True
        
        response = client.delete(
            "/transcription/tasks/mock-task-id-123",
            headers=auth_headers
        )
    
    assert response.status_code == 200
    result = response.json()
    assert "success" in result
    assert result["success"] is True
    
    # Vérifier que la mise à jour du statut a été appelée correctement
    mock_update.assert_called_once_with("mock-task-id-123", "cancelled")


def test_invalid_audio_format(auth_headers, mock_db_user):
    """Teste la validation du format audio"""
    # Créer un fichier texte temporaire
    with tempfile.NamedTemporaryFile(suffix=".txt") as temp_file:
        temp_file.write(b"Ceci n'est pas un fichier audio")
        temp_file.flush()
        
        with open(temp_file.name, "rb") as f:
            files = {"audio": ("not_audio.txt", f, "text/plain")}
            response = client.post(
                "/transcription/monologue", 
                files=files,
                data={"language": "fr", "model": "medium"},
                headers=auth_headers
            )
    
    assert response.status_code == 400
    result = response.json()
    assert "detail" in result
    assert "format" in result["detail"].lower()


def test_invalid_model_size(auth_headers, mock_db_user):
    """Teste la validation de la taille du modèle"""
    with patch("api.transcription_router.save_uploaded_file") as mock_save:
        mock_save.return_value = str(TEST_AUDIO_PATH)
        
        with open(TEST_AUDIO_PATH, "rb") as f:
            files = {"audio": ("test_audio.mp3", f, "audio/mpeg")}
            response = client.post(
                "/transcription/monologue", 
                files=files,
                data={"language": "fr", "model": "invalid_size"},
                headers=auth_headers
            )
    
    assert response.status_code == 400
    result = response.json()
    assert "detail" in result
    assert "modèle" in result["detail"].lower()


if __name__ == "__main__":
    # Pour exécuter individuellement ce fichier de test
    pytest.main(["-xvs", __file__])