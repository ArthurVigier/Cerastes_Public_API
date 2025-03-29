from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import stripe
import json
import logging
from datetime import datetime
import os

from auth import get_current_active_user
from auth_models import User, ApiKeyLevel
from database import update_user, record_subscription_event

# Configuration de Stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "sk_test_51XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

# Configuration du logging
logger = logging.getLogger("subscription_routes")

# Configuration des produits et plans Stripe
STRIPE_PLANS = {
    "basic": {
        "price_id": "price_1XXXXXXXXXXXXXXXXXXXbasic",
        "api_level": ApiKeyLevel.BASIC,
        "name": "Basic Plan"
    },
    "premium": {
        "price_id": "price_1XXXXXXXXXXXXXXXXXXXpremium",
        "api_level": ApiKeyLevel.PREMIUM,
        "name": "Premium Plan"
    },
    "enterprise": {
        "price_id": "price_1XXXXXXXXXXXXXXXXXXXenterprise",
        "api_level": ApiKeyLevel.ENTERPRISE,
        "name": "Enterprise Plan"
    }
}

# Mapper les price_id aux plans
PRICE_ID_TO_PLAN = {plan["price_id"]: {"id": plan_id, **plan} for plan_id, plan in STRIPE_PLANS.items()}

router = APIRouter(
    prefix="/api/subscriptions",
    tags=["subscriptions"],
    responses={401: {"description": "Non autorisé"}},
)

@router.get("/current")
async def get_current_subscription(current_user: User = Depends(get_current_active_user)):
    """
    Récupère l'abonnement actuel de l'utilisateur.
    """
    try:
        # Si l'utilisateur a un ID client Stripe, récupérer les informations d'abonnement
        if hasattr(current_user, "stripe_customer_id") and current_user.stripe_customer_id:
            # Récupérer les abonnements Stripe
            subscriptions = stripe.Subscription.list(
                customer=current_user.stripe_customer_id,
                status="active",
                limit=1
            )
            
            if subscriptions and subscriptions.data:
                subscription = subscriptions.data[0]
                
                # Récupérer les détails du plan
                price_id = subscription.items.data[0].price.id
                plan_details = PRICE_ID_TO_PLAN.get(price_id, {})
                
                return {
                    "subscription": {
                        "id": subscription.id,
                        "status": subscription.status,
                        "current_period_end": datetime.fromtimestamp(subscription.current_period_end).isoformat(),
                        "cancel_at_period_end": subscription.cancel_at_period_end,
                        "planId": plan_details.get("id", "unknown"),
                        "planName": plan_details.get("name", "Unknown Plan")
                    }
                }
            
        # Si aucun abonnement actif n'est trouvé
        return {
            "subscription": None
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Erreur Stripe lors de la récupération de l'abonnement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération de l'abonnement: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'abonnement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.post("/create-subscription")
async def create_subscription(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """
    Crée un nouvel abonnement Stripe pour l'utilisateur.
    """
    try:
        price_id = data.get("priceId")
        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de prix manquant"
            )
        
        # Vérifier si l'utilisateur a déjà un ID client Stripe
        customer_id = None
        if hasattr(current_user, "stripe_customer_id") and current_user.stripe_customer_id:
            customer_id = current_user.stripe_customer_id
        
        # Si l'utilisateur n'a pas d'ID client, en créer un
        if not customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name or current_user.username,
                metadata={
                    "user_id": current_user.id
                }
            )
            customer_id = customer.id
            
            # Mettre à jour l'utilisateur avec l'ID client Stripe
            current_user.stripe_customer_id = customer_id
            await update_user(current_user)
        
        # Vérifier les abonnements existants
        existing_subscriptions = stripe.Subscription.list(
            customer=customer_id,
            status="active"
        )
        
        # Si l'utilisateur a déjà un abonnement actif, le mettre à jour
        if existing_subscriptions and existing_subscriptions.data:
            existing_sub = existing_subscriptions.data[0]
            
            # Mettre à jour l'abonnement existant
            updated_subscription = stripe.Subscription.modify(
                existing_sub.id,
                items=[{
                    'id': existing_sub['items']['data'][0].id,
                    'price': price_id,
                }],
                payment_behavior='allow_incomplete',
                proration_behavior='create_prorations'
            )
            
            return {
                "clientSecret": updated_subscription.latest_invoice.payment_intent.client_secret,
                "subscription": {
                    "id": updated_subscription.id,
                    "status": updated_subscription.status
                }
            }
        
        # Créer un nouvel abonnement
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[
                {
                    "price": price_id
                }
            ],
            payment_behavior='default_incomplete',
            expand=["latest_invoice.payment_intent"]
        )
        
        return {
            "clientSecret": subscription.latest_invoice.payment_intent.client_secret,
            "subscription": {
                "id": subscription.id,
                "status": subscription.status
            }
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Erreur Stripe lors de la création de l'abonnement: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'abonnement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.post("/cancel")
async def cancel_subscription(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """
    Annule l'abonnement de l'utilisateur à la fin de la période actuelle.
    """
    try:
        subscription_id = data.get("subscriptionId")
        if not subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID d'abonnement manquant"
            )
        
        # Récupérer l'abonnement
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        # Vérifier que l'utilisateur est bien le propriétaire de l'abonnement
        if not hasattr(current_user, "stripe_customer_id") or subscription.customer != current_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas autorisé à annuler cet abonnement"
            )
        
        # Annuler l'abonnement à la fin de la période
        canceled_subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
        
        return {
            "subscription": {
                "id": canceled_subscription.id,
                "status": canceled_subscription.status,
                "cancel_at_period_end": canceled_subscription.cancel_at_period_end,
                "current_period_end": datetime.fromtimestamp(canceled_subscription.current_period_end).isoformat()
            }
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Erreur Stripe lors de l'annulation de l'abonnement: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erreur lors de l'annulation de l'abonnement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.post("/reactivate")
async def reactivate_subscription(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """
    Réactive un abonnement annulé.
    """
    try:
        subscription_id = data.get("subscriptionId")
        if not subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID d'abonnement manquant"
            )
        
        # Récupérer l'abonnement
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        # Vérifier que l'utilisateur est bien le propriétaire de l'abonnement
        if not hasattr(current_user, "stripe_customer_id") or subscription.customer != current_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas autorisé à réactiver cet abonnement"
            )
        
        # Réactiver l'abonnement
        reactivated_subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=False
        )
        
        return {
            "subscription": {
                "id": reactivated_subscription.id,
                "status": reactivated_subscription.status,
                "cancel_at_period_end": reactivated_subscription.cancel_at_period_end,
                "current_period_end": datetime.fromtimestamp(reactivated_subscription.current_period_end).isoformat()
            }
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Erreur Stripe lors de la réactivation de l'abonnement: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erreur lors de la réactivation de l'abonnement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Webhook pour recevoir les événements Stripe.
    """
    # Obtenir la charge utile de la requête
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    
    try:
        # Vérifier la signature Stripe
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        logger.error(f"Erreur de décodage de la charge utile: {e}")
        raise HTTPException(status_code=400, detail="Charge utile non valide")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Erreur de vérification de signature: {e}")
        raise HTTPException(status_code=400, detail="Signature non valide")
    
    # Traiter l'événement
    background_tasks.add_task(handle_stripe_event, event)
    
    return {"status": "success"}

async def handle_stripe_event(event):
    """
    Traite un événement Stripe en arrière-plan.
    """
    try:
        # Log de l'événement
        logger.info(f"Événement Stripe reçu: {event.type}")
        
        # Traiter différents types d'événements
        if event.type == "invoice.payment_succeeded":
            await handle_payment_succeeded(event.data.object)
        elif event.type == "invoice.payment_failed":
            await handle_payment_failed(event.data.object)
        elif event.type == "customer.subscription.created":
            await handle_subscription_created(event.data.object)
        elif event.type == "customer.subscription.updated":
            await handle_subscription_updated(event.data.object)
        elif event.type == "customer.subscription.deleted":
            await handle_subscription_deleted(event.data.object)
    except Exception as e:
        logger.error(f"Erreur lors du traitement de l'événement Stripe: {e}")

async def handle_payment_succeeded(invoice):
    """
    Traite un paiement réussi.
    """
    try:
        # Récupérer les informations client et abonnement
        subscription_id = invoice.subscription
        customer_id = invoice.customer
        
        # Récupérer l'abonnement
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        # Récupérer les détails du plan
        price_id = subscription.items.data[0].price.id
        plan_details = PRICE_ID_TO_PLAN.get(price_id, {})
        
        # Récupérer l'utilisateur à partir des métadonnées du client
        from database import get_user_by_stripe_id
        user = await get_user_by_stripe_id(customer_id)
        
        if user:
            # Mettre à jour le niveau d'API de l'utilisateur si l'abonnement est actif
            if subscription.status == "active":
                api_level = plan_details.get("api_level", ApiKeyLevel.FREE)
                user.subscription = api_level
                await update_user(user)
            
            # Enregistrer l'événement d'abonnement
            await record_subscription_event(
                user_id=user.id,
                event_type="payment_succeeded",
                subscription_id=subscription_id,
                invoice_id=invoice.id,
                amount=invoice.amount_paid / 100,  # Convertir les centimes en dollars/euros
                plan_id=plan_details.get("id", "unknown"),
                plan_name=plan_details.get("name", "Unknown Plan")
            )
            
            logger.info(f"Niveau d'API mis à jour pour l'utilisateur {user.id}: {api_level}")
    except Exception as e:
        logger.error(f"Erreur lors du traitement du paiement réussi: {e}")

async def handle_payment_failed(invoice):
    """
    Traite un paiement échoué.
    """
    try:
        # Récupérer les informations client et abonnement
        subscription_id = invoice.subscription
        customer_id = invoice.customer
        
        # Récupérer l'utilisateur à partir des métadonnées du client
        from database import get_user_by_stripe_id
        user = await get_user_by_stripe_id(customer_id)
        
        if user:
            # Enregistrer l'événement d'abonnement
            await record_subscription_event(
                user_id=user.id,
                event_type="payment_failed",
                subscription_id=subscription_id,
                invoice_id=invoice.id,
                amount=invoice.amount_due / 100,  # Convertir les centimes en dollars/euros
                error_message=invoice.last_payment_error.message if invoice.last_payment_error else "Unknown error"
            )
            
            logger.warning(f"Paiement échoué pour l'utilisateur {user.id}, abonnement {subscription_id}")
    except Exception as e:
        logger.error(f"Erreur lors du traitement du paiement échoué: {e}")

async def handle_subscription_created(subscription):
    """
    Traite la création d'un abonnement.
    """
    try:
        # Récupérer les informations client
        customer_id = subscription.customer
        
        # Récupérer les détails du plan
        price_id = subscription.items.data[0].price.id
        plan_details = PRICE_ID_TO_PLAN.get(price_id, {})
        
        # Récupérer l'utilisateur à partir des métadonnées du client
        from database import get_user_by_stripe_id
        user = await get_user_by_stripe_id(customer_id)
        
        if user:
            # Mettre à jour le niveau d'API de l'utilisateur si l'abonnement est actif
            if subscription.status == "active":
                api_level = plan_details.get("api_level", ApiKeyLevel.FREE)
                user.subscription = api_level
                await update_user(user)
            
            # Enregistrer l'événement d'abonnement
            await record_subscription_event(
                user_id=user.id,
                event_type="subscription_created",
                subscription_id=subscription.id,
                plan_id=plan_details.get("id", "unknown"),
                plan_name=plan_details.get("name", "Unknown Plan"),
                status=subscription.status
            )
            
            logger.info(f"Abonnement créé pour l'utilisateur {user.id}: {subscription.id}")
    except Exception as e:
        logger.error(f"Erreur lors du traitement de la création d'abonnement: {e}")

async def handle_subscription_updated(subscription):
    """
    Traite la mise à jour d'un abonnement.
    """
    try:
        # Récupérer les informations client
        customer_id = subscription.customer
        
        # Récupérer les détails du plan
        price_id = subscription.items.data[0].price.id
        plan_details = PRICE_ID_TO_PLAN.get(price_id, {})
        
        # Récupérer l'utilisateur à partir des métadonnées du client
        from database import get_user_by_stripe_id
        user = await get_user_by_stripe_id(customer_id)
        
        if user:
            # Mettre à jour le niveau d'API de l'utilisateur en fonction du statut de l'abonnement
            if subscription.status == "active":
                api_level = plan_details.get("api_level", ApiKeyLevel.FREE)
                user.subscription = api_level
            elif subscription.status in ["past_due", "unpaid", "canceled", "incomplete_expired"]:
                # Rétrograder au niveau gratuit si l'abonnement est inactif
                user.subscription = ApiKeyLevel.FREE
            
            await update_user(user)
            
            # Enregistrer l'événement d'abonnement
            await record_subscription_event(
                user_id=user.id,
                event_type="subscription_updated",
                subscription_id=subscription.id,
                plan_id=plan_details.get("id", "unknown"),
                plan_name=plan_details.get("name", "Unknown Plan"),
                status=subscription.status,
                cancel_at_period_end=subscription.cancel_at_period_end
            )
            
            logger.info(f"Abonnement mis à jour pour l'utilisateur {user.id}: {subscription.id}, statut: {subscription.status}")
    except Exception as e:
        logger.error(f"Erreur lors du traitement de la mise à jour d'abonnement: {e}")

async def handle_subscription_deleted(subscription):
    """
    Traite la suppression d'un abonnement.
    """
    try:
        # Récupérer les informations client
        customer_id = subscription.customer
        
        # Récupérer l'utilisateur à partir des métadonnées du client
        from database import get_user_by_stripe_id
        user = await get_user_by_stripe_id(customer_id)
        
        if user:
            # Rétrograder au niveau gratuit
            user.subscription = ApiKeyLevel.FREE
            await update_user(user)
            
            # Enregistrer l'événement d'abonnement
            await record_subscription_event(
                user_id=user.id,
                event_type="subscription_deleted",
                subscription_id=subscription.id,
                status="canceled"
            )
            
            logger.info(f"Abonnement supprimé pour l'utilisateur {user.id}: {subscription.id}")
    except Exception as e:
        logger.error(f"Erreur lors du traitement de la suppression d'abonnement: {e}")

@router.get("/plans")
async def get_plans():
    """
    Récupère la liste des plans disponibles.
    """
    try:
        # Formatage des plans pour l'interface utilisateur
        formatted_plans = []
        
        for plan_id, plan_details in STRIPE_PLANS.items():
            # Récupérer les détails du prix Stripe
            price = stripe.Price.retrieve(plan_details["price_id"], expand=["product"])
            
            formatted_plans.append({
                "id": plan_id,
                "name": plan_details["name"],
                "priceId": plan_details["price_id"],
                "price": price.unit_amount / 100,  # Convertir les centimes en dollars/euros
                "currency": price.currency,
                "interval": price.recurring.interval,
                "description": price.product.description if hasattr(price.product, "description") else None,
                "features": price.product.metadata.get("features", "").split(",") if hasattr(price.product, "metadata") else []
            })
        
        return {
            "plans": formatted_plans
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Erreur Stripe lors de la récupération des plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.get("/invoices")
async def get_invoices(current_user: User = Depends(get_current_active_user)):
    """
    Récupère les factures de l'utilisateur.
    """
    try:
        # Vérifier si l'utilisateur a un ID client Stripe
        if not hasattr(current_user, "stripe_customer_id") or not current_user.stripe_customer_id:
            return {
                "invoices": []
            }
        
        # Récupérer les factures
        invoices = stripe.Invoice.list(
            customer=current_user.stripe_customer_id,
            limit=20
        )
        
        # Formatage des factures pour l'interface utilisateur
        formatted_invoices = []
        
        for invoice in invoices.data:
            formatted_invoice = {
                "id": invoice.id,
                "number": invoice.number,
                "amount": invoice.total / 100,  # Convertir les centimes en dollars/euros
                "currency": invoice.currency,
                "status": invoice.status,
                "date": datetime.fromtimestamp(invoice.created).isoformat(),
                "due_date": datetime.fromtimestamp(invoice.due_date).isoformat() if invoice.due_date else None,
                "pdf": invoice.invoice_pdf
            }
            
            formatted_invoices.append(formatted_invoice)
        
        return {
            "invoices": formatted_invoices
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Erreur Stripe lors de la récupération des factures: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des factures: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.post("/update-payment-method")
async def update_payment_method(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """
    Met à jour la méthode de paiement de l'utilisateur.
    """
    try:
        # Vérifier si l'utilisateur a un ID client Stripe
        if not hasattr(current_user, "stripe_customer_id") or not current_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aucun client Stripe associé à cet utilisateur"
            )
        
        # Récupérer le payment_method_id
        payment_method_id = data.get("paymentMethodId")
        if not payment_method_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de méthode de paiement manquant"
            )
        
        # Attacher la méthode de paiement au client
        payment_method = stripe.PaymentMethod.attach(
            payment_method_id,
            customer=current_user.stripe_customer_id
        )
        
        # Définir comme méthode de paiement par défaut
        stripe.Customer.modify(
            current_user.stripe_customer_id,
            invoice_settings={
                "default_payment_method": payment_method_id
            }
        )
        
        return {
            "success": True,
            "payment_method": {
                "id": payment_method.id,
                "type": payment_method.type,
                "last4": payment_method.card.last4 if payment_method.type == "card" else None,
                "brand": payment_method.card.brand if payment_method.type == "card" else None,
                "exp_month": payment_method.card.exp_month if payment_method.type == "card" else None,
                "exp_year": payment_method.card.exp_year if payment_method.type == "card" else None
            }
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Erreur Stripe lors de la mise à jour de la méthode de paiement: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de la méthode de paiement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.get("/payment-methods")
async def get_payment_methods(current_user: User = Depends(get_current_active_user)):
    """
    Récupère les méthodes de paiement de l'utilisateur.
    """
    try:
        # Vérifier si l'utilisateur a un ID client Stripe
        if not hasattr(current_user, "stripe_customer_id") or not current_user.stripe_customer_id:
            return {
                "payment_methods": []
            }
        
        # Récupérer les méthodes de paiement
        payment_methods = stripe.PaymentMethod.list(
            customer=current_user.stripe_customer_id,
            type="card"
        )
        
        # Récupérer la méthode de paiement par défaut
        customer = stripe.Customer.retrieve(current_user.stripe_customer_id)
        default_payment_method_id = customer.invoice_settings.default_payment_method
        
        # Formatage des méthodes de paiement pour l'interface utilisateur
        formatted_payment_methods = []
        
        for pm in payment_methods.data:
            formatted_pm = {
                "id": pm.id,
                "type": pm.type,
                "last4": pm.card.last4 if pm.type == "card" else None,
                "brand": pm.card.brand if pm.type == "card" else None,
                "exp_month": pm.card.exp_month if pm.type == "card" else None,
                "exp_year": pm.card.exp_year if pm.type == "card" else None,
                "is_default": pm.id == default_payment_method_id
            }
            
            formatted_payment_methods.append(formatted_pm)
        
        return {
            "payment_methods": formatted_payment_methods
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Erreur Stripe lors de la récupération des méthodes de paiement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des méthodes de paiement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.delete("/payment-methods/{payment_method_id}")
async def delete_payment_method(
    payment_method_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Supprime une méthode de paiement.
    """
    try:
        # Vérifier si l'utilisateur a un ID client Stripe
        if not hasattr(current_user, "stripe_customer_id") or not current_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aucun client Stripe associé à cet utilisateur"
            )
        
        # Vérifier que la méthode de paiement appartient à l'utilisateur
        payment_methods = stripe.PaymentMethod.list(
            customer=current_user.stripe_customer_id,
            type="card"
        )
        
        payment_method_belongs_to_user = False
        for pm in payment_methods.data:
            if pm.id == payment_method_id:
                payment_method_belongs_to_user = True
                break
        
        if not payment_method_belongs_to_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cette méthode de paiement n'appartient pas à cet utilisateur"
            )
        
        # Vérifier si c'est la méthode de paiement par défaut
        customer = stripe.Customer.retrieve(current_user.stripe_customer_id)
        is_default = customer.invoice_settings.default_payment_method == payment_method_id
        
        # Si c'est la méthode par défaut et qu'il y a d'autres méthodes, en définir une autre comme défaut
        if is_default and len(payment_methods.data) > 1:
            new_default = next(pm for pm in payment_methods.data if pm.id != payment_method_id)
            stripe.Customer.modify(
                current_user.stripe_customer_id,
                invoice_settings={
                    "default_payment_method": new_default.id
                }
            )
        
        # Détacher la méthode de paiement
        stripe.PaymentMethod.detach(payment_method_id)
        
        return {"success": True}
        
    except stripe.error.StripeError as e:
        logger.error(f"Erreur Stripe lors de la suppression de la méthode de paiement: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur Stripe: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de la méthode de paiement: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )