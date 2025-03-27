import Card from '../components/ui/Card';

export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="Recent Activity">
          <p>Your recent activity will appear here.</p>
        </Card>
        
        <Card title="Statistics">
          <p>Your usage statistics will appear here.</p>
        </Card>
      </div>
    </div>
  );
}