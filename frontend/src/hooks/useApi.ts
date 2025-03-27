import { useState } from 'react';

interface ApiOptions {
  showSuccessNotification?: boolean;
  showErrorNotification?: boolean;
  successMessage?: string;
  errorMessage?: string;
}

interface ApiResponse<T = any> {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
}

export function useApi() {
  const [isLoading, setIsLoading] = useState(false);

  async function callApi<T>(
    apiCall: () => Promise<T>,
    options: ApiOptions = {}
  ): Promise<ApiResponse<T>> {
    const {
      showSuccessNotification = true,
      showErrorNotification = true,
      successMessage = 'Operation completed successfully',
      errorMessage = 'An error occurred'
    } = options;

    setIsLoading(true);
    
    try {
      const data = await apiCall();
      
      if (showSuccessNotification) {
        // Afficher une notification de succès (utiliser votre système de notification)
        console.log(successMessage);
      }
      
      return { data, error: null, isLoading: false };
    } catch (err) {
      const error = err instanceof Error ? err : new Error(errorMessage);
      
      if (showErrorNotification) {
        // Afficher une notification d'erreur (utiliser votre système de notification)
        console.error(errorMessage, error);
      }
      
      return { data: null, error, isLoading: false };
    } finally {
      setIsLoading(false);
    }
  }

  return {
    callApi,
    isLoading
  };
}