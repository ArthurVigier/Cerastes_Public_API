import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import SubscriptionPage from './components/SubscriptionPage';
import BillingPage from './components/BillingPage';
import PaymentMethodManager from './components/PaymentMethodManager';

function App() {
  return (
    <Router>
      <div>
        <h1>Bienvenue dans mon application React !</h1>
        <Routes>
          <Route path="/subscriptions" element={<SubscriptionPage />} />
          <Route path="/billing" element={<BillingPage />} />
          <Route path="/payment-methods" element={<PaymentMethodManager />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;