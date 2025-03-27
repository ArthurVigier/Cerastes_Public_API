import Card from '../components/ui/Card';

export default function AccountPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Account Settings</h1>
      
      <Card title="Profile">
        <p>Your profile settings will appear here.</p>
      </Card>
      
      <Card title="API Keys" className="mt-6">
        <p>Your API keys will appear here.</p>
      </Card>
    </div>
  );
}