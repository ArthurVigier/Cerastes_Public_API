from fastapi import APIRouter, Request, Depends, HTTPException, Response
import os
import logging
import stripe
from typing import Dict, Any, Optional
from pydantic import BaseModel

# Data models
from .response_models import SuccessResponse, ErrorResponse
from .error_handlers import APIError

# Logging configuration
logger = logging.getLogger("cerastes.api.subscription")

# Router creation
subscription_router = APIRouter(tags=["subscription"])

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# Products and prices
SUBSCRIPTION_PRODUCTS = {
    'basic': {
        'name': 'Basic Subscription',
        'price_id': os.environ.get('STRIPE_BASIC_PRICE_ID', ''),
        'features': ['Audio transcription', 'Basic video analysis']
    },
    'pro': {
        'name': 'Pro Subscription',
        'price_id': os.environ.get('STRIPE_PRO_PRICE_ID', ''),
        'features': ['Audio transcription with diarization', 'Advanced video analysis', 'Nonverbal analysis']
    },
    'enterprise': {
        'name': 'Enterprise Subscription',
        'price_id': os.environ.get('STRIPE_ENTERPRISE_PRICE_ID', ''),
        'features': ['All Pro features', 'Dedicated API', 'Priority support', 'Unlimited volume']
    }
}

# Pydantic models
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
    """Retrieves the list of available subscription plans"""
    try:
        return {
            "success": True,
            "plans": SUBSCRIPTION_PRODUCTS
        }
        
    except Exception as e:
        logger.error(f"Error retrieving plans: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving plans: {str(e)}")

@subscription_router.post('/create-checkout-session')
async def create_checkout_session(request: CheckoutSessionRequest, req: Request):
    """Creates a Stripe payment session for a subscription"""
    if request.plan not in SUBSCRIPTION_PRODUCTS:
        raise HTTPException(status_code=400, detail=f"Invalid subscription plan: '{request.plan}'")
    
    try:
        # Redirection URL after payment
        host_url = str(req.base_url)
        success_url = request.success_url or f"{host_url}payment/success"
        cancel_url = request.cancel_url or f"{host_url}payment/cancel"
        
        # Create payment session
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
        logger.error(f"Error creating payment session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating payment session: {str(e)}")

@subscription_router.post('/webhook')
async def webhook(request: Request, response: Response):
    """Webhook to receive Stripe events"""
    payload = await request.body()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        
    except ValueError:
        logger.error("Invalid payload")
        response.status_code = 400
        return {"error": "Invalid payload", "status_code": 400}
        
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature")
        response.status_code = 400
        return {"error": "Invalid signature", "status_code": 400}
    
    # Handle events
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Process completed session (e.g., activate subscription)
        logger.info(f"Payment session completed: {session.id}")
        
    elif event['type'] == 'customer.subscription.created':
        subscription = event['data']['object']
        # Process subscription creation
        logger.info(f"Subscription created: {subscription.id}")
        
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        # Process subscription update
        logger.info(f"Subscription updated: {subscription.id}")
        
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        # Process subscription deletion
        logger.info(f"Subscription deleted: {subscription.id}")
    
    return {"success": True}

@subscription_router.post('/customer-portal')
async def customer_portal(request: CustomerPortalRequest, req: Request):
    """Creates a Stripe customer portal session"""
    try:
        # Return URL
        host_url = str(req.base_url)
        return_url = request.return_url or host_url
        
        # Create portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=request.customer_id,
            return_url=return_url
        )
        
        return {
            "success": True,
            "portal_url": portal_session.url
        }
        
    except Exception as e:
        logger.error(f"Error creating portal session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating portal session: {str(e)}")