from fastapi import APIRouter, Request, Depends, HTTPException, Response
import os
import logging
import stripe
from typing import Dict, Any, Optional
from pydantic import BaseModel

# Modèles de données
from .response_models import SuccessResponse, ErrorResponse
from .error_handlers import APIError

# Configuration du logging
logger = logging.getLogger("cerastes.api.subscription")

# Création du router
subscription_router = APIRouter(tags=["subscription"])

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

# Modèles Pydantic
class CheckoutSessionRequest(BaseModel):
    plan: str
    email: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None

class CustomerPortalRequest(BaseModel):
    customer_id: str
    return_url: Optional[str] = None

@subscription_router.get('/plans')
async def get_subscription_plans():
    """Récupère la liste des plans d'abonnement disponibles"""
    try:
        return {
            "success": True,
            "plans": SUBSCRIPTION_PRODUCTS
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des plans: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des plans: {str(e)}")

@subscription_router.post('/create-checkout-session')
async def create_checkout_session(request: CheckoutSessionRequest, req: Request):
    """Crée une session de paiement Stripe pour un abonnement"""
    if request.plan not in SUBSCRIPTION_PRODUCTS:
        raise HTTPException(status_code=400, detail=f"Plan d'abonnement '{request.plan}' non valide")
    
    try:
        # URL de redirection après paiement
        host_url = str(req.base_url)
        success_url = request.success_url or f"{host_url}payment/success"
        cancel_url = request.cancel_url or f"{host_url}payment/cancel"
        
        # Créer la session de paiement
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': SUBSCRIPTION_PRODUCTS[request.plan]['price_id'],
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=request.email
        )
        
        return {
            "success": True,
            "session_id": checkout_session.id,
            "checkout_url": checkout_session.url
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la création de la session de paiement: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la session de paiement: {str(e)}")

@subscription_router.post('/webhook')
async def webhook(request: Request, response: Response):
    """Webhook pour recevoir les événements Stripe"""
    payload = await request.body()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        
    except ValueError:
        logger.error("Payload invalide")
        response.status_code = 400
        return {"error": "Payload invalide", "status_code": 400}
        
    except stripe.error.SignatureVerificationError:
        logger.error("Signature invalide")
        response.status_code = 400
        return {"error": "Signature invalide", "status_code": 400}
    
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
    
    return {"success": True}

@subscription_router.post('/customer-portal')
async def customer_portal(request: CustomerPortalRequest, req: Request):
    """Crée une session de portail client Stripe"""
    try:
        # URL de retour
        host_url = str(req.base_url)
        return_url = request.return_url or host_url
        
        # Créer la session de portail
        portal_session = stripe.billing_portal.Session.create(
            customer=request.customer_id,
            return_url=return_url
        )
        
        return {
            "success": True,
            "portal_url": portal_session.url
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la création de la session de portail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la session de portail: {str(e)}")