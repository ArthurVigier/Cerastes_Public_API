import React, { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';

import SubscriptionPage from './SubscriptionPage';
import PaymentMethodManager from './PaymentMethodManager';

// Replace with your Stripe publishable key
const stripePromise = loadStripe('pk_test_51XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX');

const BillingPage = () => {
  const [activeTab, setActiveTab] = useState('subscription');
  const [subscription, setSubscription] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [usageStats, setUsageStats] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Check if user is authenticated
    const token = localStorage.getItem('authToken');
    if (!token) {
      navigate('/login');
      return;
    }

    // Fetch billing data
    fetchBillingData();
  }, [navigate]);

  const fetchBillingData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const token = localStorage.getItem('authToken');
      
      // Fetch current subscription
      const subscriptionResponse = await axios.get('/api/subscriptions/current', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (subscriptionResponse.status === 200) {
        setSubscription(subscriptionResponse.data.subscription);
      }
      
      // Fetch invoices
      const invoicesResponse = await axios.get('/api/subscriptions/invoices', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (invoicesResponse.status === 200) {
        setInvoices(invoicesResponse.data.invoices);
      }
      
      // Fetch usage statistics
      const usageResponse = await axios.get('/api/auth/usage-stats', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (usageResponse.status === 200) {
        setUsageStats(usageResponse.data);
      }
      
    } catch (err) {
      console.error('Error fetching billing data:', err);
      setError('Unable to load billing information. Please try again later.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleCancelSubscription = async () => {
    if (!subscription) return;
    
    if (!confirm('Are you sure you want to cancel your subscription? Your plan will remain active until the end of the current billing period.')) {
      return;
    }
    
    try {
      setLoading(true);
      
      const token = localStorage.getItem('authToken');
      const response = await axios.post('/api/subscriptions/cancel', {
        subscriptionId: subscription.id
      }, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.status === 200) {
        // Refresh subscription data
        setSubscription(response.data.subscription);
        alert('Your subscription has been canceled and will end on ' + new Date(response.data.subscription.current_period_end).toLocaleDateString());
      }
      
    } catch (err) {
      console.error('Error canceling subscription:', err);
      setError('Unable to cancel subscription. Please try again later.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleReactivateSubscription = async () => {
    if (!subscription) return;
    
    try {
      setLoading(true);
      
      const token = localStorage.getItem('authToken');
      const response = await axios.post('/api/subscriptions/reactivate', {
        subscriptionId: subscription.id
      }, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.status === 200) {
        // Refresh subscription data
        setSubscription(response.data.subscription);
        alert('Your subscription has been reactivated!');
      }
      
    } catch (err) {
      console.error('Error reactivating subscription:', err);
      setError('Unable to reactivate subscription. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'subscription':
        return (
          <div>
            {subscription ? (
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="p-6">
                  <h3 className="text-lg font-medium text-gray-900">Current Subscription</h3>
                  <div className="mt-2 text-sm text-gray-600">
                    <div className="flex justify-between mb-2">
                      <span>Plan:</span>
                      <span className="font-semibold">{subscription.planName}</span>
                    </div>
                    <div className="flex justify-between mb-2">
                      <span>Status:</span>
                      <span className={`font-semibold ${subscription.status === 'active' ? 'text-green-600' : 'text-yellow-600'}`}>
                        {subscription.status.charAt(0).toUpperCase() + subscription.status.slice(1)}
                      </span>
                    </div>
                    <div className="flex justify-between mb-2">
                      <span>Current period ends:</span>
                      <span className="font-semibold">{new Date(subscription.current_period_end).toLocaleDateString()}</span>
                    </div>
                    {subscription.cancel_at_period_end && (
                      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mt-4">
                        <div className="flex">
                          <div className="flex-shrink-0">
                            <svg className="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                            </svg>
                          </div>
                          <div className="ml-3">
                            <p className="text-sm text-yellow-700">
                              Your subscription will be canceled on {new Date(subscription.current_period_end).toLocaleDateString()}.
                              <button
                                onClick={handleReactivateSubscription}
                                className="ml-2 font-medium text-yellow-700 underline"
                              >
                                Reactivate
                              </button>
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="mt-6 flex justify-between">
                    <button
                      onClick={() => setActiveTab('change')}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none"
                    >
                      Change Plan
                    </button>
                    {!subscription.cancel_at_period_end && (
                      <button
                        onClick={handleCancelSubscription}
                        className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none"
                      >
                        Cancel Subscription
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="p-6">
                  <h3 className="text-lg font-medium text-gray-900">No Active Subscription</h3>
                  <p className="mt-2 text-sm text-gray-600">
                    You don't have an active subscription yet. Choose a plan to get started.
                  </p>
                  <div className="mt-6">
                    <button
                      onClick={() => setActiveTab('change')}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none"
                    >
                      Choose a Plan
                    </button>
                  </div>
                </div>
              </div>
            )}
            
            {/* Usage Statistics */}
            {usageStats && (
              <div className="mt-8 bg-white rounded-lg shadow overflow-hidden">
                <div className="p-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Current Usage</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-blue-50 p-4 rounded-lg">
                      <div className="text-sm text-gray-500">API Requests Today</div>
                      <div className="mt-1 flex justify-between items-baseline">
                        <div className="text-2xl font-semibold text-gray-900">{usageStats.daily_requests || 0}</div>
                        <div className="text-sm text-gray-500">/ {usageStats.daily_limit || '∞'}</div>
                      </div>
                      <div className="mt-3 w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full" 
                          style={{ 
                            width: `${usageStats.daily_limit ? Math.min(100, (usageStats.daily_requests / usageStats.daily_limit) * 100) : 0}%` 
                          }}
                        ></div>
                      </div>
                    </div>
                    
                    <div className="bg-purple-50 p-4 rounded-lg">
                      <div className="text-sm text-gray-500">API Requests This Month</div>
                      <div className="mt-1 flex justify-between items-baseline">
                        <div className="text-2xl font-semibold text-gray-900">{usageStats.monthly_requests || 0}</div>
                        <div className="text-sm text-gray-500">/ {usageStats.monthly_limit || '∞'}</div>
                      </div>
                      <div className="mt-3 w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-purple-600 h-2 rounded-full" 
                          style={{ 
                            width: `${usageStats.monthly_limit ? Math.min(100, (usageStats.monthly_requests / usageStats.monthly_limit) * 100) : 0}%` 
                          }}
                        ></div>
                      </div>
                    </div>
                    
                    <div className="bg-green-50 p-4 rounded-lg">
                      <div className="text-sm text-gray-500">Total Tokens</div>
                      <div className="mt-1 text-2xl font-semibold text-gray-900">
                        {usageStats.total_tokens ? 
                          usageStats.total_tokens.toLocaleString() : 0}
                      </div>
                      <div className="mt-2 text-sm text-gray-500">
                        Input: {usageStats.total_tokens_input ? 
                          usageStats.total_tokens_input.toLocaleString() : 0}
                      </div>
                      <div className="text-sm text-gray-500">
                        Output: {usageStats.total_tokens_output ? 
                          usageStats.total_tokens_output.toLocaleString() : 0}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
        
      case 'payment':
        return (
          <Elements stripe={stripePromise}>
            <PaymentMethodManager />
          </Elements>
        );
        
      case 'invoices':
        return (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-5 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Billing History</h3>
            </div>
            <div className="bg-white">
              {invoices.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-500">No invoices found.</p>
                </div>
              ) : (
                <ul className="divide-y divide-gray-200">
                  {invoices.map((invoice) => (
                    <li key={invoice.id} className="px-6 py-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            Invoice {invoice.number}
                          </p>
                          <p className="text-sm text-gray-500">
                            {new Date(invoice.date).toLocaleDateString()}
                          </p>
                        </div>
                        <div className="flex items-center">
                          <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            invoice.status === 'paid' ? 'bg-green-100 text-green-800' :
                            invoice.status === 'open' ? 'bg-blue-100 text-blue-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}
                          </span>
                          <span className="ml-4 text-sm font-medium text-gray-900">
                            {invoice.amount.toLocaleString(undefined, {
                              style: 'currency',
                              currency: invoice.currency.toUpperCase()
                            })}
                          </span>
                          {invoice.pdf && (
                            <a
                              href={invoice.pdf}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="ml-4 text-sm font-medium text-blue-600 hover:text-blue-500"
                            >
                              PDF
                            </a>
                          )}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        );
        
      case 'change':
        return <SubscriptionPage currentSubscription={subscription} onSubscriptionChange={fetchBillingData} />;
        
      default:
        return null;
    }
  };
  
  if (loading && !subscription && !invoices && !usageStats) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <svg className="animate-spin h-12 w-12 mx-auto text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="mt-3 text-gray-600">Loading billing information...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="pb-5 border-b border-gray-200 sm:flex sm:items-center sm:justify-between">
        <h2 className="text-3xl font-bold leading-tight text-gray-900">
          Billing & Subscription
        </h2>
        <div className="mt-3 sm:mt-0">
          <Link
            to="/dashboard"
            className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
      
      {error && (
        <div className="mt-6 bg-red-50 border-l-4 border-red-400 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">
                {error}
              </p>
            </div>
          </div>
        </div>
      )}
      
      <div className="mt-6">
        <div className="sm:hidden">
          <select
            id="tabs"
            name="tabs"
            className="mt-4 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
            value={activeTab}
            onChange={(e) => setActiveTab(e.target.value)}
          >
            <option value="subscription">Subscription</option>
            <option value="payment">Payment Methods</option>
            <option value="invoices">Billing History</option>
            {activeTab === 'change' && <option value="change">Change Plan</option>}
          </select>
        </div>
        <div className="hidden sm:block">
          <nav className="flex space-x-4" aria-label="Tabs">
            <button
              onClick={() => setActiveTab('subscription')}
              className={`px-3 py-2 font-medium text-sm rounded-md ${
                activeTab === 'subscription'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Subscription
            </button>
            <button
              onClick={() => setActiveTab('payment')}
              className={`px-3 py-2 font-medium text-sm rounded-md ${
                activeTab === 'payment'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Payment Methods
            </button>
            <button
              onClick={() => setActiveTab('invoices')}
              className={`px-3 py-2 font-medium text-sm rounded-md ${
                activeTab === 'invoices'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Billing History
            </button>
            {activeTab === 'change' && (
              <button
                onClick={() => setActiveTab('change')}
                className="bg-blue-100 text-blue-700 px-3 py-2 font-medium text-sm rounded-md"
              >
                Change Plan
              </button>
            )}
          </nav>
        </div>
      </div>
      
      <div className="mt-6">
        {renderTabContent()}
      </div>
    </div>
  );
};

export default BillingPage;