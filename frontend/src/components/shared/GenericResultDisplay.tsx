import { useState } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';

interface GenericResultDisplayProps {
  result: any;
  title?: string;
}

export default function GenericResultDisplay({ result, title = "Analysis Result" }: GenericResultDisplayProps) {
  const [showRawResult, setShowRawResult] = useState(false);
  
  if (!result) return null;

  // Détermine si le résultat contient une explication simplifiée
  const hasPlainExplanation = Boolean(
    result.plain_explanation || 
    (result.result && result.result.plain_explanation)
  );
  
  // Récupère l'explication simplifiée
  const getPlainExplanation = () => {
    if (result.plain_explanation) {
      return result.plain_explanation;
    } else if (result.result && result.result.plain_explanation) {
      return result.result.plain_explanation;
    }
    return null;
  };

  // Récupère le résultat brut au format lisible
  const getRawResult = () => {
    if (typeof result === 'object') {
      return JSON.stringify(result, null, 2);
    }
    return String(result);
  };

  // Format spécifique pour les résultats de transcription
  const formatTranscriptionResult = () => {
    // Vérifier si nous avons une transcription
    if (result.transcription || (result.result && result.result.transcription)) {
      const transcription = result.transcription || (result.result && result.result.transcription);
      const segments = result.segments || (result.result && result.result.segments) || [];
      
      return (
        <div className="space-y-4">
          <h3 className="text-lg font-medium">Transcription</h3>
          <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-md">
            {transcription}
          </div>
          
          {segments.length > 0 && (
            <>
              <h3 className="text-lg font-medium mt-6">Segments</h3>
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {segments.map((segment: any, index: number) => (
                  <div key={index} className="border-b border-gray-200 dark:border-gray-700 pb-2">
                    <div className="text-sm text-gray-500">
                      [{segment.start.toFixed(2)}s - {segment.end.toFixed(2)}s]
                      {segment.speaker && <span className="ml-2 font-semibold">{segment.speaker}</span>}
                    </div>
                    <div>{segment.text}</div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      );
    }
    return null;
  };

  // Format spécifique pour les résultats d'analyse vidéo
  const formatVideoResult = () => {
    // Vérifier si nous avons des données d'analyse vidéo
    if (result.videoPath || (result.result && result.result.videoPath)) {
      const analysisType = result.analysisType || (result.result && result.result.analysisType) || "Standard";
      
      return (
        <div className="space-y-4">
          <h3 className="text-lg font-medium">Analyse Vidéo ({analysisType})</h3>
          <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-md">
            {/* Si des éléments spécifiques d'analyse vidéo existent, les afficher ici */}
            {result.result && typeof result.result === 'object' && Object.keys(result.result).map(key => {
              // Ignorer certaines clés techniques
              if (['taskId', 'status', 'startTime', 'endTime', 'plain_explanation'].includes(key)) return null;
              
              const value = result.result[key];
              if (typeof value === 'object') return null; // Ne pas afficher les objets complexes
              
              return (
                <div key={key} className="mb-2">
                  <span className="font-medium">{key}: </span>
                  <span>{String(value)}</span>
                </div>
              );
            })}
          </div>
        </div>
      );
    }
    return null;
  };

  // Récupère le texte à afficher selon les priorités
  const getDisplayText = () => {
    if (showRawResult) {
      return <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded overflow-auto max-h-[500px]">
        {getRawResult()}
      </pre>;
    }
    
    if (hasPlainExplanation && !showRawResult) {
      const explanation = getPlainExplanation();
      if (explanation) {
        return <div dangerouslySetInnerHTML={{ __html: explanation.replace(/\n/g, '<br/>') }} />;
      }
    }
    
    // Essayer d'afficher les résultats spécifiques au type
    const transcriptionView = formatTranscriptionResult();
    if (transcriptionView) return transcriptionView;
    
    const videoView = formatVideoResult();
    if (videoView) return videoView;
    
    // Par défaut, afficher des résultats génériques
    if (result.text) {
      return <div dangerouslySetInnerHTML={{ __html: result.text.replace(/\n/g, '<br/>') }} />;
    } 
    
    if (result.result) {
      if (typeof result.result === 'string') {
        return <div dangerouslySetInnerHTML={{ __html: result.result.replace(/\n/g, '<br/>') }} />;
      } else {
        return <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded overflow-auto max-h-[500px]">
          {JSON.stringify(result.result, null, 2)}
        </pre>;
      }
    }
    
    return <p>Résultat reçu mais format non reconnu.</p>;
  };

  return (
    <Card title={title} className="mt-8">
      <div className="mb-4 flex justify-end">
        <Button 
          variant={showRawResult ? "primary" : "secondary"}
          onClick={() => setShowRawResult(!showRawResult)}
        >
          {showRawResult ? "Affichage simplifié" : "Raw Result"}
        </Button>
      </div>
      <div className="prose dark:prose-invert max-w-none">
        {getDisplayText()}
      </div>
    </Card>
  );
}