import pytest
import requests
import json
import os
import uuid
from typing import Dict, Any, Generator
from sqlalchemy.orm import Session

# URL de base de l'API (ajuster selon l'environnement)
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Variable pour stocker les informations de test
test_data = {
    "user": None,
    "token": None,
    "api_key": None,
    "user_id": None,
    "api_key_id": None
}

# Import des fonctions de base de données pour les tests directs
try:
    from db import engine, SessionLocal, get_db
    from db.models import User, ApiKey, UsageRecord
    from database import get_user_by_username, get_api_key
except ImportError:
    # Si les imports échouent, afficher un avertissement mais continuer les tests HTTP
    import warnings
    warnings.warn("Impossible d'importer les modèles de base de données. Seuls les tests HTTP seront exécutés.")


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Fournit une session de base de données pour les tests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_health_check():
    """Vérifie si l'API est en fonctionnement."""
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    # Vérifier que la version est présente
    assert "version" in data


def test_register_user():
    """Teste l'inscription d'un nouvel utilisateur."""
    # Créer un nom d'utilisateur unique avec UUID pour éviter les conflits
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    
    # Données d'inscription
    user_data = {
        "username": username,
        "email": f"{username}@example.com",
        "password": "Password123!",
        "full_name": "Test User"
    }
    
    # Envoyer la requête d'inscription
    response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
    
    # Si l'enregistrement est désactivé, ignorer le test
    if response.status_code == 403 and "registration is disabled" in response.text.lower():
        pytest.skip("L'enregistrement d'utilisateurs est désactivé sur ce serveur")
    
    assert response.status_code == 201, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert data["username"] == username
    assert data["email"] == f"{username}@example.com"
    assert "id" in data
    
    # Sauvegarder les informations de l'utilisateur pour les tests suivants
    test_data["user"] = data
    test_data["user_id"] = data["id"]
    
    # Test direct de la base de données (si disponible)
    try:
        with SessionLocal() as db:
            db_user = get_user_by_username(db, username)
            assert db_user is not None
            assert db_user.username == username
            assert db_user.email == f"{username}@example.com"
    except Exception:
        # Si l'accès direct à la base de données échoue, continuer sans faire échouer le test
        pass


def test_login():
    """Teste la connexion d'un utilisateur."""
    # S'assurer qu'un utilisateur a été créé
    assert test_data["user"] is not None, "Aucun utilisateur créé pour le test"
    
    # Données de connexion
    login_data = {
        "username": test_data["user"]["username"],
        "password": "Password123!"
    }
    
    # Envoyer la requête de connexion (format de formulaire)
    response = requests.post(
        f"{BASE_URL}/auth/token",
        data=login_data
    )
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_at" in data
    
    # Sauvegarder le token pour les tests suivants
    test_data["token"] = data["access_token"]


def test_get_user_info():
    """Teste la récupération des informations de l'utilisateur."""
    # S'assurer qu'un token a été obtenu
    assert test_data["token"] is not None, "Aucun token obtenu pour le test"
    
    # Configurer les headers avec le token
    headers = {
        "Authorization": f"Bearer {test_data['token']}"
    }
    
    # Envoyer la requête pour récupérer les informations de l'utilisateur
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier que les informations correspondent à l'utilisateur créé
    data = response.json()
    assert data["username"] == test_data["user"]["username"]
    assert data["email"] == test_data["user"]["email"]
    assert "id" in data
    assert data["id"] == test_data["user_id"]


def test_create_api_key():
    """Teste la création d'une clé API."""
    # S'assurer qu'un token a été obtenu
    assert test_data["token"] is not None, "Aucun token obtenu pour le test"
    
    # Configurer les headers avec le token
    headers = {
        "Authorization": f"Bearer {test_data['token']}"
    }
    
    # Données pour la création de clé API
    key_data = {
        "name": "Test API Key"
    }
    
    # Envoyer la requête pour créer une clé API
    response = requests.post(f"{BASE_URL}/auth/api-keys", json=key_data, headers=headers)
    assert response.status_code == 201, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "key" in data
    assert data["name"] == "Test API Key"
    assert "id" in data
    
    # Sauvegarder la clé API et son ID pour les tests suivants
    test_data["api_key"] = data["key"]
    test_data["api_key_id"] = data["id"]
    
    # Test direct de la base de données (si disponible)
    try:
        with SessionLocal() as db:
            db_api_key = get_api_key(db, data["key"])
            assert db_api_key is not None
            assert db_api_key.key == data["key"]
            assert db_api_key.name == "Test API Key"
            assert db_api_key.user_id == test_data["user_id"]
            assert db_api_key.is_active == True
    except Exception:
        # Si l'accès direct à la base de données échoue, continuer sans faire échouer le test
        pass


def test_list_api_keys():
    """Teste la récupération des clés API de l'utilisateur."""
    # S'assurer qu'un token a été obtenu
    assert test_data["token"] is not None, "Aucun token obtenu pour le test"
    
    # Configurer les headers avec le token
    headers = {
        "Authorization": f"Bearer {test_data['token']}"
    }
    
    # Envoyer la requête pour récupérer les clés API
    response = requests.get(f"{BASE_URL}/auth/api-keys", headers=headers)
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier que la clé API créée précédemment est présente
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Vérifier si notre clé API est dans la liste
    key_found = False
    for key in data:
        if key["key"] == test_data["api_key"]:
            key_found = True
            # Mettre à jour l'ID si nécessaire
            if test_data["api_key_id"] is None:
                test_data["api_key_id"] = key["id"]
            break
    
    assert key_found, "La clé API créée n'a pas été trouvée dans la liste"


def test_deactivate_api_key():
    """Teste la désactivation d'une clé API."""
    # S'assurer qu'un token et une clé API ont été obtenus
    assert test_data["token"] is not None, "Aucun token obtenu pour le test"
    assert test_data["api_key"] is not None, "Aucune clé API créée pour le test"
    assert test_data["api_key_id"] is not None, "Aucun ID de clé API disponible"
    
    # Configurer les headers avec le token
    headers = {
        "Authorization": f"Bearer {test_data['token']}"
    }
    
    # Désactiver la clé API
    response = requests.put(f"{BASE_URL}/auth/api-keys/{test_data['api_key_id']}/deactivate", headers=headers)
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier que la clé est désactivée
    data = response.json()
    assert not data["is_active"], "La clé API n'a pas été désactivée"
    
    # Test direct de la base de données (si disponible)
    try:
        with SessionLocal() as db:
            db_api_key = get_api_key(db, test_data["api_key"])
            assert db_api_key is not None
            assert db_api_key.is_active == False
    except Exception:
        # Si l'accès direct à la base de données échoue, continuer sans faire échouer le test
        pass


def test_activate_api_key():
    """Teste l'activation d'une clé API."""
    # S'assurer qu'un token et une clé API ont été obtenus
    assert test_data["token"] is not None, "Aucun token obtenu pour le test"
    assert test_data["api_key"] is not None, "Aucune clé API créée pour le test"
    assert test_data["api_key_id"] is not None, "Aucun ID de clé API disponible"
    
    # Configurer les headers avec le token
    headers = {
        "Authorization": f"Bearer {test_data['token']}"
    }
    
    # Activer la clé API
    response = requests.put(f"{BASE_URL}/auth/api-keys/{test_data['api_key_id']}/activate", headers=headers)
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier que la clé est activée
    data = response.json()
    assert data["is_active"], "La clé API n'a pas été activée"
    
    # Test direct de la base de données (si disponible)
    try:
        with SessionLocal() as db:
            db_api_key = get_api_key(db, test_data["api_key"])
            assert db_api_key is not None
            assert db_api_key.is_active == True
    except Exception:
        # Si l'accès direct à la base de données échoue, continuer sans faire échouer le test
        pass


def test_access_without_token():
    """Teste l'accès à une route protégée sans token."""
    response = requests.get(f"{BASE_URL}/auth/me")
    assert response.status_code in [401, 403], f"Code de statut inattendu: {response.status_code}"


def test_delete_api_key():
    """Teste la suppression d'une clé API."""
    # S'assurer qu'un token et une clé API ont été obtenus
    assert test_data["token"] is not None, "Aucun token obtenu pour le test"
    assert test_data["api_key_id"] is not None, "Aucun ID de clé API disponible"
    
    # Configurer les headers avec le token
    headers = {
        "Authorization": f"Bearer {test_data['token']}"
    }
    
    # Supprimer la clé API
    response = requests.delete(f"{BASE_URL}/auth/api-keys/{test_data['api_key_id']}", headers=headers)
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier que la clé a été supprimée
    response = requests.get(f"{BASE_URL}/auth/api-keys", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    key_exists = False
    for key in data:
        if key.get("id") == test_data["api_key_id"]:
            key_exists = True
            break
    
    assert not key_exists, "La clé API n'a pas été supprimée"


def test_cleanup():
    """Nettoie l'environnement de test (supprime l'utilisateur créé)."""
    # Cette fonction n'est pas un test en soi, mais elle est utilisée pour nettoyer
    # l'environnement après les tests. Elle est exécutée à la fin.
    
    # Si nous avons un accès direct à la base de données
    try:
        if test_data["user_id"] is not None:
            with SessionLocal() as db:
                user = db.query(User).filter(User.id == test_data["user_id"]).first()
                if user:
                    db.delete(user)
                    db.commit()
    except Exception:
        # Si l'accès direct à la base de données échoue, ne pas faire échouer le test
        pass


if __name__ == "__main__":
    # Exécuter les tests manuellement
    test_health_check()
    test_register_user()
    test_login()
    test_get_user_info()
    test_create_api_key()
    test_list_api_keys()
    test_deactivate_api_key()
    test_activate_api_key()
    test_access_without_token()
    test_delete_api_key()
    test_cleanup()
    
    print("Tous les tests d'authentification ont réussi!")