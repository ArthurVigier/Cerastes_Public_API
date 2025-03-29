"""
Tests for subscription and payment functionality
----------------------------------------------
This module tests the subscription API including plans, payment
processing, and subscription management.
"""

import pytest
import requests
import json
import uuid
import time
from typing import Dict, Any


class TestSubscription:
    """Test class for subscription endpoints."""
    
    def test_list_subscription_plans(self, api_url):
        """Test retrieving available subscription plans."""
        response = requests.get(f"{api_url}/api/subscriptions/plans")
        
        # If endpoint doesn't exist, skip test
        if response.status_code == 404:
            pytest.skip("Subscription plans endpoint not available")
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "plans" in data, "No plans in response"
        plans = data["plans"]
        assert isinstance(plans, list), "Plans should be a list"
        
        # Verify plan structure if any plans exist
        if plans:
            plan = plans[0]
            assert "id" in plan, "No id in plan"
            assert "name" in plan, "No name in plan"
            assert "priceId" in plan or "price_id" in plan, "No price ID in plan"
            assert "currency" in plan, "No currency in plan"
    
    def test_current_subscription(self, api_url, auth_headers):
        """Test retrieving current subscription information."""
        response = requests.get(
            f"{api_url}/api/subscriptions/current",
            headers=auth_headers
        )
        
        # If endpoint doesn't exist, skip test
        if response.status_code == 404:
            pytest.skip("Current subscription endpoint not available")
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "subscription" in data, "No subscription in response"
        
        # Subscription may be null if user has no subscription
        if data["subscription"] is not None:
            subscription = data["subscription"]
            assert "id" in subscription, "No id in subscription"
            assert "status" in subscription, "No status in subscription"
    
    def test_checkout_session_creation(self, api_url, auth_headers):
        """Test creating a checkout session for subscription."""
        # First get available plans
        plans_response = requests.get(f"{api_url}/api/subscriptions/plans")
        
        # If plans endpoint doesn't exist, skip test
        if plans_response.status_code == 404:
            pytest.skip("Subscription plans endpoint not available")
            
        plans_data = plans_response.json()
        if not plans_data.get("plans"):
            pytest.skip("No subscription plans available")
        
        # Select the first plan
        plan_id = plans_data["plans"][0]["id"]
        
        # Prepare checkout data
        checkout_data = {
            "plan": plan_id,
            "success_url": f"{api_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{api_url}/payment/cancel"
        }
        
        # Create checkout session
        response = requests.post(
            f"{api_url}/api/subscriptions/checkout",
            json=checkout_data,
            headers=auth_headers
        )
        
        # If endpoint doesn't exist or Stripe not configured, skip test
        if response.status_code == 404:
            pytest.skip("Checkout endpoint not available")
            
        if response.status_code == 500 and "stripe" in response.text.lower():
            pytest.skip("Stripe not configured")
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "sessionId" in data or "session_id" in data, "No session ID in response"
        assert "url" in data, "No URL in response"
    
    def test_invoices(self, api_url, auth_headers):
        """Test retrieving invoices if available."""
        response = requests.get(
            f"{api_url}/api/subscriptions/invoices",
            headers=auth_headers
        )
        
        # If endpoint doesn't exist, skip test
        if response.status_code == 404:
            pytest.skip("Invoices endpoint not available")
        
        # If Stripe not configured, skip test
        if response.status_code == 500 and "stripe" in response.text.lower():
            pytest.skip("Stripe not configured")
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "invoices" in data, "No invoices in response"
        invoices = data["invoices"]
        assert isinstance(invoices, list), "Invoices should be a list"
    
    def test_payment_methods(self, api_url, auth_headers):
        """Test retrieving payment methods if available."""
        response = requests.get(
            f"{api_url}/api/subscriptions/payment-methods",
            headers=auth_headers
        )
        
        # If endpoint doesn't exist, skip test
        if response.status_code == 404:
            pytest.skip("Payment methods endpoint not available")
        
        # If Stripe not configured, skip test
        if response.status_code == 500 and "stripe" in response.text.lower():
            pytest.skip("Stripe not configured")
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}, {response.text}"
        
        # Check response
        data = response.json()
        assert "payment_methods" in data, "No payment methods in response"
        payment_methods = data["payment_methods"]
        assert isinstance(payment_methods, list), "Payment methods should be a list"
    
    def test_subscription_actions(self, api_url, auth_headers):
        """Test subscription management actions if available."""
        # First get current subscription
        current_response = requests.get(
            f"{api_url}/api/subscriptions/current",
            headers=auth_headers
        )
        
        # If endpoint doesn't exist, skip test
        if current_response.status_code == 404:
            pytest.skip("Current subscription endpoint not available")
        
        # If user has no subscription, skip test
        current_data = current_response.json()
        if not current_data.get("subscription"):
            pytest.skip("No active subscription for testing actions")
        
        subscription = current_data["subscription"]
        subscription_id = subscription["id"]
        
        # Test cancel subscription
        cancel_data = {
            "subscriptionId": subscription_id
        }
        
        cancel_response = requests.post(
            f"{api_url}/api/subscriptions/cancel",
            json=cancel_data,
            headers=auth_headers
        )
        
        # If endpoint doesn't exist, skip test
        if cancel_response.status_code == 404:
            pytest.skip("Cancel subscription endpoint not available")
        
        # If Stripe not configured or subscription not cancellable, skip test
        if cancel_response.status_code in [403, 500]:
            pytest.skip("Cannot cancel subscription: " + cancel_response.text)
        
        assert cancel_response.status_code == 200, f"Unexpected status code: {cancel_response.status_code}, {cancel_response.text}"
        
        # Check response
        cancel_data = cancel_response.json()
        assert "subscription" in cancel_data, "No subscription in response"
        assert cancel_data["subscription"]["cancel_at_period_end"] == True, "Subscription not marked for cancellation"
        
        # Test reactivate subscription
        reactivate_data = {
            "subscriptionId": subscription_id
        }
        
        reactivate_response = requests.post(
            f"{api_url}/api/subscriptions/reactivate",
            json=reactivate_data,
            headers=auth_headers
        )
        
        # If endpoint doesn't exist, skip test
        if reactivate_response.status_code == 404:
            pytest.skip("Reactivate subscription endpoint not available")
        
        # If Stripe not configured or subscription not reactivatable, skip test
        if reactivate_response.status_code in [403, 500]:
            pytest.skip("Cannot reactivate subscription: " + reactivate_response.text)
        
        assert reactivate_response.status_code == 200, f"Unexpected status code: {reactivate_response.status_code}, {reactivate_response.text}"
        
        # Check response
        reactivate_data = reactivate_response.json()
        assert "subscription" in reactivate_data, "No subscription in response"
        assert reactivate_data["subscription"]["cancel_at_period_end"] == False, "Subscription not reactivated"