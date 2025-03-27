import apiClient from '../client';
import { INFERENCE_ENDPOINTS } from '../../constants/endpoint';

export interface InferenceRequest {
    text: string;
    model?: string;
    max_tokens?: number;
    temperature?: number;
    use_segmentation?: boolean;
  }
  
  // Mise à jour pour inclure un résultat direct optionnel
  export interface InferenceResponse {
    taskId: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    result?: string | any;  // Résultat direct optionnel, peut être une chaîne ou un objet
    plain_explanation?: string; // Explication simplifiée du résultat
    error?: string;   // Message d'erreur optionnel
  }
  
  export interface InferenceResult {
    taskId: string;
    status: 'completed' | 'failed';
    result: string | any; // Peut être un texte ou un objet JSON complexe
    plain_explanation?: string; // Explication en langage naturel générée par JSONSimplifier
    error?: string;
    model: string;
    startTime: string;
    endTime: string;
    processingTime: number;
  }
  
  // Mise à jour pour inclure un champ d'erreur
  export interface InferenceStatus {
    taskId: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress?: number;
    startTime: string;
    estimatedCompletionTime?: string;
    result?: string | any; // Résultat partiel possible
    plain_explanation?: string; // Explication simplifiée possible
    error?: string;  // Message d'erreur optionnel
  }
  

export const inferenceService = {
  startInference: async (data: InferenceRequest): Promise<InferenceResponse> => {
    const response = await apiClient.post(INFERENCE_ENDPOINTS.START, data);
    return response.data;
  },
  
  getStatus: async (taskId: string): Promise<InferenceStatus> => {
    const response = await apiClient.get(`${INFERENCE_ENDPOINTS.STATUS}/${taskId}`);
    return response.data;
  },
  
  getResult: async (taskId: string): Promise<InferenceResult> => {
    const response = await apiClient.get(`${INFERENCE_ENDPOINTS.RESULT}/${taskId}`);
    return response.data;
  },

  getAvailableModels: async () => {
    const response = await apiClient.get(INFERENCE_ENDPOINTS.MODELS);
    return response.data;
  },
  
  getHistory: async (limit: number = 10, offset: number = 0) => {
    const response = await apiClient.get(`${INFERENCE_ENDPOINTS.HISTORY}?limit=${limit}&offset=${offset}`);
    return response.data;
  }
};