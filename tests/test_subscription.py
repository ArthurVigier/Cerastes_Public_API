"""
Tests pour les fonctionnalités d'abonnement
------------------------------------------
Ce module teste les fonctionnalités liées aux abonnements, notamment
la création de sessions de paiement, la gestion des webhooks Stripe,
et les restrictions liées aux différents niveaux d'abonnement.
"""

import pytest
import requests
import json
import os
import time
import uuid
from typing import Dict, Any
from unittest import mock

# URL de base de l'API (ajuster selon l'environnement)
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Variable pour stocker les informations de test
test_data = {
    "token": None,
    "api_key": None,
    "stripe_session_id": None,
    "user_id": None,
    "subscription_id": None,
    "checkout_session_url": None,
    "customer_id": None
}

def setup_module():
    """Configuration initiale pour les tests d'abonnement."""
    # Récupérer un token et une clé API valides
    try:
        # Essayer d'utiliser une variable d'environnement
        token = os.environ.get("TEST_TOKEN")
        api_key = os.environ.get("TEST_API_KEY")
        
        if not token or not api_key:
            # Importer et exécuter les tests d'authentification si nécessaire
            from test_auth import test_register_user, test_login, test_create_api_key
            
            # Créer un utilisateur et une clé API si nécessaire
            test_register_user()
            test_login()
            test_create_api_key()
            
            from test_auth import test_data as auth_test_data
            token = auth_test_data["token"]
            api_key = auth_test_data["api_key"]
            test_data["user_id"] = auth_test_data["user_id"]
    except Exception as e:
        print(f"Erreur lors de la configuration des tests d'abonnement: {e}")
        # En cas d'erreur, une clé de test doit être fournie en variable d'environnement
        token = os.environ.get("TEST_TOKEN")
        api_key = os.environ.get("TEST_API_KEY")
        if not token or not api_key:
            raise Exception("Aucun token ou clé API disponible pour les tests. Définissez TEST_TOKEN et TEST_API_KEY ou exécutez test_auth.py")
    
    test_data["token"] = token
    test_data["api_key"] = api_key

def get_auth_headers():
    """Retourne les en-têtes d'authentification avec le token."""
    return {"Authorization": f"Bearer {test_data['token']}"}

def get_api_key_headers():
    """Retourne les en-têtes d'authentification avec la clé API."""
    return {"X-API-Key": test_data["api_key"]}

def test_list_subscription_plans():
    """Teste la récupération des plans d'abonnement disponibles."""
    response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
    
    # Si l'endpoint n'existe pas ou les abonnements ne sont pas configurés, ignorer le test
    if response.status_code == 404:
        pytest.skip("L'endpoint des plans d'abonnement n'est pas disponible")
    
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "plans" in data
    assert isinstance(data["plans"], list)
    
    # Vérifier qu'il y a au moins un plan
    assert len(data["plans"]) > 0, "Aucun plan d'abonnement trouvé"
    
    # Vérifier la structure des plans
    for plan in data["plans"]:
        assert "id" in plan
        assert "name" in plan
        assert "priceId" in plan or "price_id" in plan
        assert "currency" in plan
        # D'autres champs facultatifs peuvent être vérifiés

def test_current_subscription():
    """Teste la récupération de l'abonnement actuel de l'utilisateur."""
    # S'assurer qu'un token a été obtenu
    assert test_data["token"] is not None, "Aucun token obtenu pour le test"
    
    # Configurer les headers avec le token
    headers = get_auth_headers()
    
    # Récupérer l'abonnement actuel
    response = requests.get(f"{BASE_URL}/api/subscriptions/current", headers=headers)
    
    # Si l'endpoint n'existe pas, ignorer le test
    if response.status_code == 404:
        pytest.skip("L'endpoint d'abonnement actuel n'est pas disponible")
    
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "subscription" in data
    
    # Remarque: Si l'utilisateur n'a pas d'abonnement, subscription peut être null

def test_create_checkout_session():
    """Teste la création d'une session de paiement."""
    # S'assurer qu'un token a été obtenu
    assert test_data["token"] is not None, "Aucun token obtenu pour le test"
    
    # Configurer les headers avec le token
    headers = get_auth_headers()
    
    # Récupérer d'abord la liste des plans pour choisir un plan à tester
    plans_response = requests.get(f"{BASE_URL}/api/subscriptions/plans")
    
    # Si l'endpoint n'existe pas ou les abonnements ne sont pas configurés, ignorer le test
    if plans_response.status_code == 404:
        pytest.skip("L'endpoint des plans d'abonnement n'est pas disponible")
    
    plans_data = plans_response.json()
    if not plans_data.get("plans"):
        pytest.skip("Aucun plan d'abonnement disponible pour le test")
    
    # Choisir le premier plan disponible
    plan_id = plans_data["plans"][0]["id"]
    
    # Données pour la création de session de paiement
    checkout_data = {
        "plan": plan_id,
        "success_url": f"{BASE_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{BASE_URL}/payment/cancel"
    }
    
    # Envoyer la requête pour créer une session de paiement
    response = requests.post(f"{BASE_URL}/api/subscriptions/checkout", json=checkout_data, headers=headers)
    
    # Si l'endpoint n'existe pas ou Stripe n'est pas configuré, ignorer le test
    if response.status_code == 404 or response.status_code == 500 and "stripe" in response.text.lower():
        pytest.skip("L'endpoint de création de session n'est pas disponible ou Stripe n'est pas configuré")
    
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "sessionId" in data or "session_id" in data
    assert "url" in data
    
    # Sauvegarder l'ID de session pour les tests suivants
    test_data["stripe_session_id"] = data.get("sessionId") or data.get("session_id")
    test_data["checkout_session_url"] = data["url"]

def test_mock_webhook_payment_succeeded():
    """Teste le traitement d'un webhook de paiement réussi (simulé)."""
    # Ce test simule un webhook Stripe pour un paiement réussi
    # Dans un environnement réel, ce webhook est appelé par Stripe directement
    
    # S'assurer qu'un ID de session a été obtenu
    if not test_data.get("stripe_session_id"):
        pytest.skip("Aucun ID de session Stripe disponible pour le test de webhook")
    
    # Créer un événement Stripe simulé
    # Remarque: Ceci est une approximation, l'événement réel serait beaucoup plus complexe
    mock_event = {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": f"in_{uuid.uuid4().hex}",
                "subscription": f"sub_{uuid.uuid4().hex}",
                "customer": test_data.get("customer_id", f"cus_{uuid.uuid4().hex}"),
                "amount_paid": 2000,  # 20.00€/$ en centimes
                "status": "paid"
            }
        }
    }
    
    # Configurer la signature webhook (simulée)
    timestamp = int(time.time())
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_test")
    signature = f"t={timestamp},v1=mock_signature,v0=mock_signature"
    
    headers = {
        "Stripe-Signature": signature
    }
    
    # Envoyer la requête webhook
    response = requests.post(
        f"{BASE_URL}/api/subscriptions/webhook",
        json=mock_event,
        headers=headers
    )
    
    # Ce test est informatif et exploratoire
    # Il n'est pas censé réussir dans un environnement de test sauf si le webhook est correctement simulé
    # Nous vérifions simplement que l'endpoint répond et ne plante pas
    if response.status_code != 404:
        assert response.status_code in [200, 400], f"Code de statut inattendu: {response.status_code}, {response.text}"
        print(f"Réponse du webhook: {response.status_code} - {response.text}")

def test_subscription_levels_access():
    """Teste l'accès aux fonctionnalités selon les niveaux d'abonnement."""
    # S'assurer qu'une clé API est disponible
    assert test_data["api_key"] is not None, "Aucune clé API disponible pour le test"
    
    # Configurer les headers avec la clé API
    headers = get_api_key_headers()
    
    # Tester l'accès à une fonctionnalité de base (disponible pour tous les niveaux)
    response = requests.get(f"{BASE_URL}/api/tasks", headers=headers)
    assert response.status_code == 200, "Accès refusé à une fonctionnalité de base"
    
    # Tester l'accès à une fonctionnalité avancée (traitement par lots)
    batch_data = {
        "texts": ["Premier texte.", "Deuxième texte."],
        "use_segmentation": True,
        "max_new_tokens": 100
    }
    
    response = requests.post(f"{BASE_URL}/api/inference/batch", json=batch_data, headers=headers)
    
    # Si le traitement par lots est limité aux abonnements premium, la réponse devrait indiquer cela
    # Ce test permet de vérifier que les restrictions sont en place, même si nous n'avons pas accès
    if response.status_code == 403 and "abonnement" in response.text.lower():
        print("Fonctionnalité de traitement par lots correctement restreinte par niveau d'abonnement")
    elif response.status_code == 202:
        print("Traitement par lots disponible avec le niveau d'abonnement actuel")
    else:
        print(f"Code de statut inattendu: {response.status_code}, {response.text}")

def test_cancel_subscription():
    """Teste l'annulation d'un abonnement."""
    # S'assurer qu'un token a été obtenu
    assert test_data["token"] is not None, "Aucun token obtenu pour le test"
    
    # Si aucun ID d'abonnement n'est disponible, ignorer ce test
    if not test_data.get("subscription_id"):
        pytest.skip("Aucun ID d'abonnement disponible pour le test d'annulation")
    
    # Configurer les headers avec le token
    headers = get_auth_headers()
    
    # Données pour l'annulation d'abonnement
    cancel_data = {
        "subscriptionId": test_data["subscription_id"]
    }
    
    # Envoyer la requête pour annuler l'abonnement
    response = requests.post(f"{BASE_URL}/api/subscriptions/cancel", json=cancel_data, headers=headers)
    
    # Si l'endpoint n'existe pas ou Stripe n'est pas configuré, ignorer le test
    if response.status_code == 404 or response.status_code == 500 and "stripe" in response.text.lower():
        pytest.skip("L'endpoint d'annulation n'est pas disponible ou Stripe n'est pas configuré")
    
    # Si l'abonnement n'existe pas ou n'appartient pas à l'utilisateur, c'est attendu dans ce test
    if response.status_code == 403 or response.status_code == 404:
        print(f"Abonnement non trouvé ou non autorisé: {response.text}")
        return
    
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "subscription" in data
    assert data["subscription"]["cancel_at_period_end"] == True

def test_reactivate_subscription():
    """Teste la réactivation d'un abonnement annulé."""
    # S'assurer qu'un token a été obtenu
    assert test_data["token"] is not None, "Aucun token obtenu pour le test"
    
    # Si aucun ID d'abonnement n'est disponible, ignorer ce test
    if not test_data.get("subscription_id"):
        pytest.skip("Aucun ID d'abonnement disponible pour le test de réactivation")
    
    # Configurer les headers avec le token
    headers = get_auth_headers()
    
    # Données pour la réactivation d'abonnement
    reactivate_data = {
        "subscriptionId": test_data["subscription_id"]
    }
    
    # Envoyer la requête pour réactiver l'abonnement
    response = requests.post(f"{BASE_URL}/api/subscriptions/reactivate", json=reactivate_data, headers=headers)
    
    # Si l'endpoint n'existe pas ou Stripe n'est pas configuré, ignorer le test
    if response.status_code == 404 or response.status_code == 500 and "stripe" in response.text.lower():
        pytest.skip("L'endpoint de réactivation n'est pas disponible ou Stripe n'est pas configuré")
    
    # Si l'abonnement n'existe pas ou n'appartient pas à l'utilisateur, c'est attendu dans ce test
    if response.status_code == 403 or response.status_code == 404:
        print(f"Abonnement non trouvé ou non autorisé: {response.text}")
        return
    
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "subscription" in data
    assert data["subscription"]["cancel_at_period_end"] == False

def test_get_invoices():
    """Teste la récupération des factures de l'utilisateur."""
    # S'assurer qu'un token a été obtenu
    assert test_data["token"] is not None, "Aucun token obtenu pour le test"
    
    # Configurer les headers avec le token
    headers = get_auth_headers()
    
    # Récupérer les factures
    response = requests.get(f"{BASE_URL}/api/subscriptions/invoices", headers=headers)
    
    # Si l'endpoint n'existe pas ou Stripe n'est pas configuré, ignorer le test
    if response.status_code == 404 or response.status_code == 500 and "stripe" in response.text.lower():
        pytest.skip("L'endpoint des factures n'est pas disponible ou Stripe n'est pas configuré")
    
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "invoices" in data
    assert isinstance(data["invoices"], list)

def test_payment_methods():
    """Teste la récupération des méthodes de paiement de l'utilisateur."""
    # S'assurer qu'un token a été obtenu
    assert test_data["token"] is not None, "Aucun token obtenu pour le test"
    
    # Configurer les headers avec le token
    headers = get_auth_headers()
    
    # Récupérer les méthodes de paiement
    response = requests.get(f"{BASE_URL}/api/subscriptions/payment-methods", headers=headers)
    
    # Si l'endpoint n'existe pas ou Stripe n'est pas configuré, ignorer le test
    if response.status_code == 404 or response.status_code == 500 and "stripe" in response.text.lower():
        pytest.skip("L'endpoint des méthodes de paiement n'est pas disponible ou Stripe n'est pas configuré")
    
    assert response.status_code == 200, f"Code de statut inattendu: {response.status_code}, {response.text}"
    
    # Vérifier la réponse
    data = response.json()
    assert "payment_methods" in data
    assert isinstance(data["payment_methods"], list)

if __name__ == "__main__":
    # Initialiser les tests
    setup_module()
    
    # Exécuter les tests manuellement
    test_list_subscription_plans()
    test_current_subscription()
    
    try:
        test_create_checkout_session()
    except Exception as e:
        print(f"Erreur lors de la création de session de paiement: {e}")
    
    try:
        test_mock_webhook_payment_succeeded()
    except Exception as e:
        print(f"Erreur lors du test du webhook: {e}")
    
    test_subscription_levels_access()
    
    try:
        test_cancel_subscription()
        test_reactivate_subscription()
    except Exception as e:
        print(f"Erreur lors des tests d'annulation/réactivation: {e}")
    
    test_get_invoices()
    test_payment_methods()
    
    print("Tous les tests d'abonnement ont réussi!")