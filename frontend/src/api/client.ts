import axios from 'axios';
import { API_BASE_URL } from '../constants/endpoint';

// Créer une instance axios avec la configuration de base
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // timeout de 60 secondes pour les opérations longues
});

// Intercepteur pour ajouter le token d'authentification aux requêtes
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Récupérer la clé API si disponible
    const apiKey = localStorage.getItem('apiKey');
    if (apiKey && !config.headers.Authorization) {
      config.headers['X-API-Key'] = apiKey;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Intercepteur pour gérer les erreurs de réponse
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
    // Gestion du rafraîchissement du token si 401 et pas déjà tenté
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        // Tenter de rafraîchir le token
        const refreshToken = localStorage.getItem('refreshToken');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          
          const { token } = response.data;
          localStorage.setItem('authToken', token);
          
          // Réessayer la requête originale avec le nouveau token
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        // Si le rafraîchissement échoue, rediriger vers la page de connexion
        localStorage.removeItem('authToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
      }
    }
    
    // Gérer les erreurs API de manière générale
    const errorMessage = error.response?.data?.message || error.message || 'Une erreur est survenue';
    
    // On peut émettre un événement pour afficher une notification d'erreur
    const errorEvent = new CustomEvent('api-error', { 
      detail: { message: errorMessage, status: error.response?.status } 
    });
    window.dispatchEvent(errorEvent);
    
    return Promise.reject(error);
  }
);

export default apiClient;