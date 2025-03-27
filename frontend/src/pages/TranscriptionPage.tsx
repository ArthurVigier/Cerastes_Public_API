import Card from '../components/ui/Card';

export default function TranscriptionPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Audio Transcription</h1>
      
      <Card>
        <p className="mb-4">Upload an audio file to transcribe it.</p>
        <button className="btn btn-primary">Upload Audio</button>
      </Card>
    </div>
  );
}