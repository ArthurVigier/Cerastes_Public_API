import React, { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { CardElement, Elements, useStripe, useElements } from '@stripe/react-stripe-js';
import axios from 'axios';

// Replace with your Stripe publishable key
const stripePromise = loadStripe('pk_test_51XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX');

const PaymentMethodForm = ({ onSuccess, onCancel }) => {
  const stripe = useStripe();
  const elements = useElements();
  const [error, setError] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [cardComplete, setCardComplete] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!stripe || !elements) {
      // Stripe.js has not loaded yet
      return;
    }

    if (!cardComplete) {
      setError('Please complete your card information.');
      return;
    }

    setProcessing(true);
    setError(null);

    try {
      const cardElement = elements.getElement(CardElement);
      
      const { error, paymentMethod } = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
      });

      if (error) {
        setError(error.message);
        setProcessing(false);
        return;
      }

      // Send the payment method to your server
      const token = localStorage.getItem('authToken');
      const response = await axios.post('/api/subscriptions/update-payment-method', {
        paymentMethodId: paymentMethod.id
      }, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.status === 200) {
        onSuccess(response.data.payment_method);
      } else {
        setError('An error occurred while saving your payment method.');
      }
    } catch (err) {
      setError(err.message || 'An error occurred.');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Card Information
        </label>
        <div className="p-3 border rounded-md">
          <CardElement
            options={{
              style: {
                base: {
                  fontSize: '16px',
                  color: '#424770',
                  '::placeholder': {
                    color: '#aab7c4',
                  },
                },
                invalid: {
                  color: '#9e2146',
                },
              },
            }}
            onChange={(e) => setCardComplete(e.complete)}
          />
        </div>
      </div>

      {error && (
        <div className="text-red-600 text-sm" role="alert">
          {error}
        </div>
      )}

      <div className="flex justify-end space-x-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={!stripe || processing || !cardComplete}
          className="px-4 py-2 bg-blue-600 border border-transparent rounded-md shadow-sm text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {processing ? 'Saving...' : 'Save Card'}
        </button>
      </div>
    </form>
  );
};

const PaymentMethod = ({ method, isDefault, onDelete, onMakeDefault }) => {
  return (
    <div className="flex items-center justify-between p-4 border rounded-md mb-4">
      <div className="flex items-center space-x-4">
        {/* Card brand logo */}
        <div className="text-xl">
          {method.brand === 'visa' && '💳 Visa'}
          {method.brand === 'mastercard' && '💳 Mastercard'}
          {method.brand === 'amex' && '💳 American Express'}
          {method.brand === 'discover' && '💳 Discover'}
          {method.brand === 'diners' && '💳 Diners Club'}
          {method.brand === 'jcb' && '💳 JCB'}
          {method.brand === 'unionpay' && '💳 UnionPay'}
          {!['visa', 'mastercard', 'amex', 'discover', 'diners', 'jcb', 'unionpay'].includes(method.brand) && '💳 Card'}
        </div>
        
        <div>
          <div className="font-medium">
            •••• {method.last4}
          </div>
          <div className="text-sm text-gray-600">
            Expires {method.exp_month.toString().padStart(2, '0')}/{method.exp_year.toString().substring(2)}
            {isDefault && <span className="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">Default</span>}
          </div>
        </div>
      </div>
      
      <div className="flex space-x-2">
        {!isDefault && (
          <button
            onClick={() => onMakeDefault(method.id)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Make Default
          </button>
        )}
        <button
          onClick={() => onDelete(method.id)}
          className="text-sm text-red-600 hover:text-red-800"
        >
          Remove
        </button>
      </div>
    </div>
  );
};

const PaymentMethodManager = () => {
  const [paymentMethods, setPaymentMethods] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [actionInProgress, setActionInProgress] = useState(false);

  useEffect(() => {
    fetchPaymentMethods();
  }, []);

  const fetchPaymentMethods = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const token = localStorage.getItem('authToken');
      const response = await axios.get('/api/subscriptions/payment-methods', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.status === 200) {
        setPaymentMethods(response.data.payment_methods);
      }
    } catch (err) {
      setError('Unable to load payment methods. Please try again later.');
      console.error('Error fetching payment methods:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddNewCard = () => {
    setShowAddForm(true);
  };

  const handleFormCancel = () => {
    setShowAddForm(false);
  };

  const handleFormSuccess = (newMethod) => {
    setShowAddForm(false);
    fetchPaymentMethods(); // Refresh the list
  };

  const handleDeletePaymentMethod = async (paymentMethodId) => {
    if (!confirm('Are you sure you want to remove this payment method?')) {
      return;
    }
    
    try {
      setActionInProgress(true);
      
      const token = localStorage.getItem('authToken');
      const response = await axios.delete(`/api/subscriptions/payment-methods/${paymentMethodId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.status === 200) {
        fetchPaymentMethods(); // Refresh the list
      }
    } catch (err) {
      setError('Unable to delete payment method. Please try again later.');
      console.error('Error deleting payment method:', err);
    } finally {
      setActionInProgress(false);
    }
  };

  const handleMakeDefault = async (paymentMethodId) => {
    try {
      setActionInProgress(true);
      
      const token = localStorage.getItem('authToken');
      const response = await axios.post('/api/subscriptions/update-payment-method', {
        paymentMethodId: paymentMethodId,
        makeDefault: true
      }, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.status === 200) {
        fetchPaymentMethods(); // Refresh the list
      }
    } catch (err) {
      setError('Unable to update default payment method. Please try again later.');
      console.error('Error updating default payment method:', err);
    } finally {
      setActionInProgress(false);
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Payment Methods</h2>
      
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      
      {loading ? (
        <div className="text-center py-8">
          <svg className="animate-spin h-8 w-8 mx-auto text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="mt-2 text-gray-600">Loading payment methods...</p>
        </div>
      ) : (
        <>
          {paymentMethods.length === 0 ? (
            <div className="text-center py-8 bg-gray-50 rounded-md">
              <p className="text-gray-600 mb-4">You don't have any payment methods yet.</p>
              <button
                onClick={handleAddNewCard}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Add Payment Method
              </button>
            </div>
          ) : (
            <div className="mb-6">
              {paymentMethods.map((method) => (
                <PaymentMethod
                  key={method.id}
                  method={method}
                  isDefault={method.is_default}
                  onDelete={handleDeletePaymentMethod}
                  onMakeDefault={handleMakeDefault}
                />
              ))}
              
              <div className="mt-4">
                <button
                  onClick={handleAddNewCard}
                  disabled={actionInProgress}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {actionInProgress ? 'Please wait...' : 'Add Payment Method'}
                </button>
              </div>
            </div>
          )}
        </>
      )}
      
      {showAddForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-xl font-bold mb-4">Add New Payment Method</h3>
            <Elements stripe={stripePromise}>
              <PaymentMethodForm
                onSuccess={handleFormSuccess}
                onCancel={handleFormCancel}
              />
            </Elements>
          </div>
        </div>
      )}
    </div>
  );
};

export default PaymentMethodManager;