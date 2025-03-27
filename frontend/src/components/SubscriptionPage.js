import React, { useState } from 'react';

const plans = [
  {
    id: 'free',
    name: 'FREE',
    price: 'Free',
    description: 'Basic access with significant limitations.',
    details: [
      'Daily requests limited (50)',
      'Short texts only (10K characters)',
      'No batch processing',
      'No access to advanced models'
    ]
  },
  {
    id: 'basic',
    name: 'BASIC',
    price: '$19/month',
    description: 'Entry-level paid plan.',
    details: [
      'Increased daily requests (200)',
      'Longer texts (50K characters)',
      'Batch processing available',
      'No access to advanced models'
    ]
  },
  {
    id: 'premium',
    name: 'PREMIUM',
    price: '$49/month',
    description: 'Advanced plan for higher demands.',
    details: [
      'High number of daily requests (1000)',
      'Long texts (200K characters)',
      'Batch processing available',
      'Access to advanced models'
    ]
  },
  {
    id: 'enterprise',
    name: 'ENTERPRISE',
    price: '$199/month',
    description: 'Maximum level plan for enterprise needs.',
    details: [
      'Very high daily requests (5000)',
      'Very long texts (500K characters)',
      'Priority batch processing',
      'Full access to advanced models'
    ]
  }
];

const SubscriptionPage = () => {
  const [email, setEmail] = useState('');
  const [selectedPlan, setSelectedPlan] = useState('free');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubscribe = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      // Call your subscription API endpoint (adjust the URL as needed)
      const response = await fetch('/api/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, plan: selectedPlan })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Subscription error.');
      }

      await response.json();
      setMessage('Subscription successful!');
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="subscription-page" style={{ maxWidth: '600px', margin: '0 auto', padding: '1rem' }}>
      <h1>Subscribe</h1>
      <form onSubmit={handleSubscribe}>
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="email">Email Address:</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ width: '100%', padding: '0.5rem', marginTop: '0.5rem' }}
          />
        </div>
        <div style={{ marginBottom: '1rem' }}>
          <label>Select a plan:</label>
          {plans.map((plan) => (
            <div key={plan.id} style={{ border: '1px solid #ccc', padding: '1rem', marginTop: '1rem', borderRadius: '5px' }}>
              <div>
                <input
                  type="radio"
                  id={plan.id}
                  name="plan"
                  value={plan.id}
                  checked={selectedPlan === plan.id}
                  onChange={() => setSelectedPlan(plan.id)}
                />
                <label htmlFor={plan.id} style={{ fontWeight: 'bold', marginLeft: '0.5rem' }}>
                  {plan.name} ({plan.price})
                </label>
              </div>
              <p>{plan.description}</p>
              <ul>
                {plan.details.map((detail, index) => (
                  <li key={index}>{detail}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <button type="submit" disabled={loading} style={{ padding: '0.75rem 1.5rem' }}>
          {loading ? 'Processing...' : 'Subscribe'}
        </button>
      </form>
      {message && <p style={{ marginTop: '1rem' }}>{message}</p>}
    </div>
  );
};

export default SubscriptionPage;
