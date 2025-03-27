import { useState } from 'react';
import Card from '../components/ui/Card';
import InferenceForm from '../components/inference/InferenceForm';
import ResultDisplay from '../components/inference/ResultDisplay';

export default function InferencePage() {
  const [result, setResult] = useState<any>(null);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Text Analysis</h1>
      
      <Card>
        <InferenceForm onResultReceived={setResult} />
      </Card>
      
      {result && <ResultDisplay result={result} />}
    </div>
  );
}