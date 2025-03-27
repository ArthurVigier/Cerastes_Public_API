import { useState } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';

// Interface typée pour les résultats d'API
interface ApiResult {
  text?: string;
  result?: any; 
  plain_explanation?: string;
  [key: string]: any; // Pour les autres propriétés potentielles
}

interface ResultDisplayProps {
  result: ApiResult;
  title?: string; // Ajout d'un titre personnalisable
}

export default function ResultDisplay({ result, title = "Analysis Result" }: ResultDisplayProps) {
  // État pour basculer entre l'affichage simplifié et le résultat brut
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
      // Exclusion de plain_explanation pour ne montrer que les données brutes
      const { plain_explanation, ...rawData } = result;
      return JSON.stringify(rawData, null, 2);
    }
    return String(result); // Conversion explicite en string pour éviter des problèmes de type
  };

  // Récupère le texte à afficher selon les priorités
  const getDisplayText = () => {
    if (showRawResult) {
      return (
        <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded overflow-auto max-h-[500px] text-sm">
          {getRawResult()}
        </pre>
      );
    }
    
    if (hasPlainExplanation && !showRawResult) {
      const explanation = getPlainExplanation();
      if (!explanation) return <p>No explanation available.</p>;
      
      return (
        <div 
          className="prose-lg" 
          dangerouslySetInnerHTML={{ __html: explanation.replace(/\n/g, '<br/>') }} 
        />
      );
    }
    
    if (result.text) {
      return (
        <div dangerouslySetInnerHTML={{ __html: result.text.replace(/\n/g, '<br/>') }} />
      );
    } 
    
    if (result.result) {
      if (typeof result.result === 'string') {
        return (
          <div dangerouslySetInnerHTML={{ __html: result.result.replace(/\n/g, '<br/>') }} />
        );
      } else {
        return (
          <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded overflow-auto max-h-[500px] text-sm">
            {JSON.stringify(result.result, null, 2)}
          </pre>
        );
      }
    }
    
    return <p>Result received but unrecognized format.</p>;
  };

  return (
    <Card title={title} className="mt-8">
      <div className="mb-4 flex justify-end">
        <Button 
          variant={showRawResult ? "primary" : "secondary"}
          onClick={() => setShowRawResult(!showRawResult)}
        >
          {showRawResult ? "Show Simplified Result" : "Raw Result"}
        </Button>
      </div>
      <div className="prose dark:prose-invert max-w-none">
        {getDisplayText()}
      </div>
    </Card>
  );
}