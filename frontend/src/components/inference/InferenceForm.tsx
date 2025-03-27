import { useState } from 'react';
import Button from '../ui/Button';
import { inferenceService, InferenceResult, InferenceResponse } from '../../api/services/inference';
import { useApi } from '../../hooks/useApi';

// Définir clairement le type du résultat attendu
interface InferenceFormProps {
  onResultReceived: (result: InferenceResult) => void;
}

export default function InferenceForm({ onResultReceived }: InferenceFormProps) {
  const [text, setText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [model, setModel] = useState('default');
  const { callApi } = useApi();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);
    
    try {
      const { data, error } = await callApi<InferenceResponse>(
        () => inferenceService.startInference({ 
          text,
          model: model !== 'default' ? model : undefined,
          use_segmentation: true
        }),
        {
          showSuccessNotification: false,
          errorMessage: 'Error processing text'
        }
      );
      
      if (data && !error) {
        // Si l'API renvoie un résultat directement (mode synchrone)
        if (data.result) {
          // Convertir la réponse au format attendu par onResultReceived
          const formattedResult: InferenceResult = {
            taskId: data.taskId,
            status: data.status as 'completed' | 'failed',
            result: data.result,
            error: data.error,
            model: model !== 'default' ? model : 'default',
            startTime: new Date().toISOString(),
            endTime: new Date().toISOString(),
            processingTime: 0
          };
          onResultReceived(formattedResult);
        } 
        // Si l'API renvoie un ID de tâche pour un traitement asynchrone
        else if (data.taskId) {
          await pollTaskResult(data.taskId);
        }
      }
    } finally {
      setIsProcessing(false);
    }
  };
  
  const pollTaskResult = async (taskId: string) => {
    let attempts = 0;
    const maxAttempts = 30;
    const intervalMs = 2000;
    
    const checkStatus = async () => {
      attempts++;
      
      try {
        const statusResponse = await inferenceService.getStatus(taskId);
        
        if (statusResponse.status === 'completed') {
          const resultResponse = await inferenceService.getResult(taskId);
          onResultReceived(resultResponse);
          return true;
        } else if (statusResponse.status === 'failed') {
          throw new Error(statusResponse.error || 'Processing failed');
        } else if (attempts >= maxAttempts) {
          throw new Error('Timeout exceeded');
        }
        
        return false;
      } catch (error) {
        console.error('Error checking status:', error);
        throw error;
      }
    };
    
    const poll = async () => {
      try {
        const isDone = await checkStatus();
        if (!isDone) {
          setTimeout(poll, intervalMs);
        }
      } catch (error) {
        console.error('Polling error:', error);
        setIsProcessing(false);
      }
    };
    
    poll();
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="text" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Your text
        </label>
        <textarea
          id="text"
          rows={8}
          className="input font-mono"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter your text here..."
          required
        />
      </div>
      
      <div>
        <label htmlFor="model" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Model to use
        </label>
        <select
          id="model"
          className="input"
          value={model}
          onChange={(e) => setModel(e.target.value)}
        >
          <option value="default">Default model</option>
          <option value="llama-3-70b-instruct">LLaMA 3 (70B) - High precision</option>
          <option value="llama-3-8b-instruct">LLaMA 3 (8B) - Balanced</option>
          <option value="mistral-7b-instruct">Mistral (7B) - Fast</option>
        </select>
      </div>
      
      <div>
        <Button
          type="submit"
          isLoading={isProcessing}
          disabled={text.trim().length === 0}
          className="w-full"
        >
          {isProcessing ? 'Processing...' : 'Analyze Text'}
        </Button>
      </div>
    </form>
  );
}