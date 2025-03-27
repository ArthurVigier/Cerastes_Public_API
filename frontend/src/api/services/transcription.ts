import apiClient from '../client';
import { TRANSCRIPTION_ENDPOINTS } from '../../api/endpoint';

export interface TranscriptionRequest {
    file_path?: string;
    language?: string;
    model_size?: string;
    diarize?: boolean;
    min_speakers?: number;
    max_speakers?: number;
}

export interface TranscriptionUploadResponse {
    audio_path: string;
    message?: string;
}

export interface TranscriptionResponse {
    taskId: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    message?: string;
    progress?: number;
    error?: string;
}

export interface TranscriptionSegment {
    start: number;
    end: number;
    text: string;
    speaker?: string;
}

export interface TranscriptionResult {
    taskId: string;
    status: 'completed' | 'failed';
    result: {
        transcription: string;
        segments: TranscriptionSegment[];
        language?: string;
        duration?: number;
        speakers?: string[];
    };
    plain_explanation?: string; // Explication en langage naturel générée par JSONSimplifier
    error?: string;
    model?: string;
    startTime: string;
    endTime: string;
    processingTime: number;
    file_path?: string;
}

export interface TranscriptionStatus {
    taskId: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress?: number;
    message?: string;
    startTime: string;
    estimatedCompletionTime?: string;
    result?: any; // Résultat partiel possible
    plain_explanation?: string; // Explication simplifiée possible
    error?: string;
}

export const transcriptionService = {
    // Télécharger un fichier audio
    uploadAudio: async (file: File): Promise<TranscriptionUploadResponse> => {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await apiClient.post('/api/transcription/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },
    
    // Démarrer une transcription monologue
    startMonologueTranscription: async (data: TranscriptionRequest): Promise<TranscriptionResponse> => {
        const response = await apiClient.post('/api/transcription/monologue', data);
        return response.data;
    },
    
    // Démarrer une transcription avec identification des locuteurs
    startMultiSpeakerTranscription: async (data: TranscriptionRequest): Promise<TranscriptionResponse> => {
        const response = await apiClient.post('/api/transcription/multiple_speakers', data);
        return response.data;
    },
    
    // Démarrer une transcription (endpoint générique)
    startTranscription: async (data: TranscriptionRequest): Promise<TranscriptionResponse> => {
        const response = await apiClient.post(TRANSCRIPTION_ENDPOINTS.START, data);
        return response.data;
    },
    
    // Obtenir le statut d'une tâche de transcription
    getStatus: async (taskId: string): Promise<TranscriptionStatus> => {
        const response = await apiClient.get(`${TRANSCRIPTION_ENDPOINTS.STATUS}/${taskId}`);
        return response.data;
    },
    
    // Obtenir le résultat d'une transcription
    getResult: async (taskId: string): Promise<TranscriptionResult> => {
        const response = await apiClient.get(`${TRANSCRIPTION_ENDPOINTS.RESULT}/${taskId}`);
        return response.data;
    },
    
    // Obtenir les modèles de transcription disponibles
    getAvailableModels: async () => {
        const response = await apiClient.get(TRANSCRIPTION_ENDPOINTS.MODELS);
        return response.data;
    }
};