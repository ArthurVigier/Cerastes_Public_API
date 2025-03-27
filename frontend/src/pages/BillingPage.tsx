import Card from '../components/ui/Card';

export default function BillingPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Billing & Subscription</h1>
      
      <Card title="Current Plan">
        <p>Your subscription plan information will appear here.</p>
      </Card>
      
      <Card title="Payment Methods" className="mt-6">
        <p>Your payment methods will appear here.</p>
      </Card>
    </div>
  );
}