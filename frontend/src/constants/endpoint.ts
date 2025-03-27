/**
 * Définition des endpoints de l'API
 */

// Base API URL - utilise l'URL définie dans les variables d'environnement ou une valeur par défaut
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// Endpoints d'authentification
export const AUTH_ENDPOINTS = {
  LOGIN: '/auth/token',
  REGISTER: '/auth/register',
  REFRESH: '/auth/refresh',
  PROFILE: '/auth/profile',
  API_KEYS: '/auth/api-keys',
  CREATE_API_KEY: '/auth/api-keys/create',
  REVOKE_API_KEY: '/auth/api-keys/revoke',
};

// Endpoints d'inférence
export const INFERENCE_ENDPOINTS = {
  START: '/api/inference/start',
  STATUS: '/api/tasks',
  RESULT: '/api/inference/result',
  MODELS: '/api/inference/models',
  HISTORY: '/api/inference/history',
};

// Endpoints de transcription
export const TRANSCRIPTION_ENDPOINTS = {
  START: '/api/transcription/start',
  STATUS: '/api/tasks',
  RESULT: '/api/transcription/result',
  MODELS: '/api/transcription/models',
};

// Endpoints d'analyse vidéo
export const VIDEO_ENDPOINTS = {
  START: '/api/video/start',
  STATUS: '/api/tasks',
  RESULT: '/api/video/result',
  MODELS: '/api/video/models',
};

// Endpoints de gestion des tâches
export const TASK_ENDPOINTS = {
  LIST: '/api/tasks',
  GET: '/api/tasks',
  CANCEL: '/api/tasks',
  RETRY: '/api/tasks',
};

// Endpoints d'abonnement
export const SUBSCRIPTION_ENDPOINTS = {
  PLANS: '/api/subscription/plans',
  CURRENT: '/api/subscription/current',
  SUBSCRIBE: '/api/subscription/subscribe',
  CANCEL: '/api/subscription/cancel',
  INVOICES: '/api/subscription/invoices',
  PAYMENT_METHODS: '/api/subscription/payment-methods',
};

// Endpoints de santé
export const HEALTH_ENDPOINTS = {
  CHECK: '/api/health',
  MODELS: '/api/health/models',
};