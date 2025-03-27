export const AUTH_ENDPOINTS = {
    LOGIN: '/auth/token',
    REGISTER: '/auth/register',
    API_KEYS: '/auth/api-keys',
};
  
export const INFERENCE_ENDPOINTS = {
    START: '/api/inference/start',
    STATUS: '/api/tasks',  // Mise à jour: utiliser l'endpoint de tâches générique
    RESULT: '/api/inference/result',
    MODELS: '/api/inference/models',  // Ajout pour la cohérence avec constants/endpoint.ts
    HISTORY: '/api/inference/history',  // Ajout pour la cohérence avec constants/endpoint.ts
};
  
export const MEDIA_ENDPOINTS = {
    TRANSCRIPTION: '/api/transcription/start',  // Mise à jour pour correspondre à l'endpoint exact
    VIDEO_ANALYSIS: '/api/video/analysis',  // Mise à jour pour l'endpoint correct
    UPLOAD: '/api/upload',
};
  
export const BILLING_ENDPOINTS = {
    PLANS: '/api/subscription/plans',
    SUBSCRIBE: '/api/subscription/subscribe',
    INVOICES: '/api/subscription/invoices',
};
  
export const TASK_ENDPOINTS = {
    LIST: '/api/tasks',
    DETAIL: (id: string) => `/api/tasks/${id}`,
    CANCEL: (id: string) => `/api/tasks/${id}/cancel`,
};

// Ajout des endpoints spécifiques pour la transcription
export const TRANSCRIPTION_ENDPOINTS = {
    START: '/api/transcription/start',
    STATUS: '/api/tasks',
    RESULT: '/api/transcription/result',
    MODELS: '/api/transcription/models',
};

// Ajout des endpoints spécifiques pour l'analyse vidéo
export const VIDEO_ENDPOINTS = {
    START: '/api/video/start',
    STATUS: '/api/tasks',
    RESULT: '/api/video/result',
    MODELS: '/api/video/models',
};