from flask import Blueprint, request, jsonify, redirect, url_for, current_app
import os
import logging
import stripe
from typing import Dict, Any

# Import des modèles de réponse
from .response_models import (
    SuccessResponse,
    ErrorResponse
)
from .error_handlers import APIError

# Configuration du logging
logger = logging.getLogger("cerastes.api.subscription")

# Création du blueprint
subscription_bp = Blueprint('subscription', __name__, url_prefix='/api/subscription')

# Configuration Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# Produits et prix
SUBSCRIPTION_PRODUCTS = {
    'basic': {
        'name': 'Abonnement Basic',
        'price_id': os.environ.get('STRIPE_BASIC_PRICE_ID', ''),
        'features': ['Transcription audio', 'Analyse vidéo basique']
    },
    'pro': {
        'name': 'Abonnement Pro',
        'price_id': os.environ.get('STRIPE_PRO_PRICE_ID', ''),
        'features': ['Transcription audio avec diarisation', 'Analyse vidéo avancée', 'Analyse non-verbale']
    },
    'enterprise': {
        'name': 'Abonnement Enterprise',
        'price_id': os.environ.get('STRIPE_ENTERPRISE_PRICE_ID', ''),
        'features': ['Fonctionnalités Pro', 'API dédiée', 'Support prioritaire', 'Volume illimité']
    }
}

@subscription_bp.route('/plans', methods=['GET'])
def get_subscription_plans():
    """Récupère la liste des plans d'abonnement disponibles"""
    try:
        return jsonify({
            "success": True,
            "plans": SUBSCRIPTION_PRODUCTS
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des plans: {str(e)}")
        raise APIError(f"Erreur lors de la récupération des plans: {str(e)}", 500)

@subscription_bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Crée une session de paiement Stripe pour un abonnement"""
    data = request.json
    if not data or 'plan' not in data:
        raise APIError("Plan d'abonnement non spécifié", 400)
    
    plan = data['plan']
    if plan not in SUBSCRIPTION_PRODUCTS:
        raise APIError(f"Plan d'abonnement '{plan}' non valide", 400)
    
    customer_email = data.get('email')
    
    try:
        # URL de redirection après paiement
        success_url = data.get('success_url', request.host_url + 'payment/success')
        cancel_url = data.get('cancel_url', request.host_url + 'payment/cancel')
        
        # Créer la session de paiement
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': SUBSCRIPTION_PRODUCTS[plan]['price_id'],
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=customer_email
        )
        
        return jsonify({
            "success": True,
            "session_id": checkout_session.id,
            "checkout_url": checkout_session.url
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la création de la session de paiement: {str(e)}")
        raise APIError(f"Erreur lors de la création de la session de paiement: {str(e)}", 500)

@subscription_bp.route('/webhook', methods=['POST'])
def webhook():
    """Webhook pour recevoir les événements Stripe"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        
    except ValueError as e:
        logger.error("Payload invalide")
        return jsonify(ErrorResponse(error="Payload invalide", status_code=400).dict()), 400
        
    except stripe.error.SignatureVerificationError as e:
        logger.error("Signature invalide")
        return jsonify(ErrorResponse(error="Signature invalide", status_code=400).dict()), 400
    
    # Gérer les événements
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Traiter la session complétée (par exemple, activer l'abonnement)
        logger.info(f"Session de paiement complétée: {session.id}")
        
    elif event['type'] == 'customer.subscription.created':
        subscription = event['data']['object']
        # Traiter la création d'abonnement
        logger.info(f"Abonnement créé: {subscription.id}")
        
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        # Traiter la mise à jour d'abonnement
        logger.info(f"Abonnement mis à jour: {subscription.id}")
        
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        # Traiter la suppression d'abonnement
        logger.info(f"Abonnement supprimé: {subscription.id}")
    
    return jsonify({"success": True})

@subscription_bp.route('/customer-portal', methods=['POST'])
def customer_portal():
    """Crée une session de portail client Stripe"""
    data = request.json
    if not data or 'customer_id' not in data:
        raise APIError("ID client non spécifié", 400)
    
    customer_id = data['customer_id']
    return_url = data.get('return_url', request.host_url)
    
    try:
        # Créer la session de portail
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )
        
        return jsonify({
            "success": True,
            "portal_url": portal_session.url
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la création de la session de portail: {str(e)}")
        raise APIError(f"Erreur lors de la création de la session de portail: {str(e)}", 500)