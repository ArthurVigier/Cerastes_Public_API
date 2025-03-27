import apiClient from '../client';
import { VIDEO_ENDPOINTS } from '../../api/endpoint';

export interface VideoAnalysisRequest {
    video_path: string;
    analysis_type?: string;
    extract_frames?: boolean;
    frame_count?: number;
    analyze_facial_expressions?: boolean;
    transcribe?: boolean;
    diarize?: boolean;
    language?: string;
}

export interface VideoUploadResponse {
    video_path: string;
    message?: string;
}

export interface VideoExtractionRequest {
    video_path: string;
    extract_type?: 'standard' | 'nonverbal';
}

export interface VideoExtractionResponse {
    content: string;
    file_path: string;
    message?: string;
}

export interface VideoResponse {
    taskId: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress?: number;
    message?: string;
    result?: any;
    plain_explanation?: string; // Explication simplifiée du résultat
    error?: string;
}

export interface VideoResult {
    taskId: string;
    status: 'completed' | 'failed';
    result: any; // Peut être un objet JSON complexe avec les résultats d'analyse vidéo
    plain_explanation?: string; // Explication en langage naturel générée par JSONSimplifier
    error?: string;
    model?: string;
    startTime: string;
    endTime: string;
    processingTime: number;
    videoPath?: string;
    extractionType?: string;
    analysisType?: string;
}

export interface VideoStatus {
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

export const videoService = {
    uploadVideo: async (file: File): Promise<VideoUploadResponse> => {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await apiClient.post('/api/video/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },
    
    startVideoAnalysis: async (data: VideoAnalysisRequest): Promise<VideoResponse> => {
        const response = await apiClient.post(VIDEO_ENDPOINTS.START, data);
        return response.data;
    },
    
    getVideoStatus: async (taskId: string): Promise<VideoStatus> => {
        const response = await apiClient.get(`${VIDEO_ENDPOINTS.STATUS}/${taskId}`);
        return response.data;
    },
    
    getVideoResult: async (taskId: string): Promise<VideoResult> => {
        const response = await apiClient.get(`${VIDEO_ENDPOINTS.RESULT}/${taskId}`);
        return response.data;
    },
    
    startManipulationAnalysis: async (videoPath: string): Promise<VideoResponse> => {
        const response = await apiClient.post('/api/video/manipulation-analysis', {
            video_path: videoPath
        });
        return response.data;
    },
    
    startNonverbalAnalysis: async (videoPath: string): Promise<VideoResponse> => {
        const response = await apiClient.post('/api/video/nonverbal-analysis', {
            video_path: videoPath
        });
        return response.data;
    },
    
    extractVideoContent: async (videoPath: string, extractType: string = 'standard'): Promise<VideoExtractionResponse> => {
        const response = await apiClient.post('/api/video/extract', {
            video_path: videoPath,
            extract_type: extractType
        });
        return response.data;
    },
    
    getAvailableModels: async () => {
        const response = await apiClient.get(VIDEO_ENDPOINTS.MODELS);
        return response.data;
    }
};