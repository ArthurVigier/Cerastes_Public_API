import Card from '../components/ui/Card';

export default function VideoPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Video Analysis</h1>
      
      <Card>
        <p className="mb-4">Upload a video file to analyze it.</p>
        <button className="btn btn-primary">Upload Video</button>
      </Card>
    </div>
  );
}