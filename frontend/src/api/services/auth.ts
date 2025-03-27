import apiClient from '../client';
import { AUTH_ENDPOINTS } from '../../constants/endpoint'; 

export interface LoginData {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
}

export const authService = {
  login: async (data: LoginData) => {
    const response = await apiClient.post(AUTH_ENDPOINTS.LOGIN, data);
    return response.data;
  },
  
  register: async (data: RegisterData) => {
    const response = await apiClient.post(AUTH_ENDPOINTS.REGISTER, data);
    return response.data;
  },
  
  getApiKeys: async () => {
    const response = await apiClient.get(AUTH_ENDPOINTS.API_KEYS);
    return response.data;
  },
  
  createApiKey: async (name: string) => {
    const response = await apiClient.post(AUTH_ENDPOINTS.API_KEYS, { name });
    return response.data;
  },
  
  deleteApiKey: async (id: string) => {
    const response = await apiClient.delete(`${AUTH_ENDPOINTS.API_KEYS}/${id}`);
    return response.data;
  }
};