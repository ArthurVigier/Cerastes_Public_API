import { useEffect, useState } from 'react';
import { useAuthStore } from '../store/auth';
import { authService, LoginData, RegisterData } from '../api/services/auth';
import { useUIStore } from '../store/ui';

export function useAuth() {
  const { token, user, isAuthenticated, login: storeLogin, logout: storeLogout, setApiKey } = useAuthStore();
  const addNotification = useUIStore((state) => state.addNotification);
  const [isLoading, setIsLoading] = useState(false);

  // Check for token on load
  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    const storedApiKey = localStorage.getItem('apiKey');
    
    if (storedToken && storedUser) {
      storeLogin(storedToken, JSON.parse(storedUser));
    }
    
    if (storedApiKey) {
      setApiKey(storedApiKey);
    }
  }, []);

  const login = async (data: LoginData) => {
    setIsLoading(true);
    try {
      const response = await authService.login(data);
      const { access_token, user } = response;
      
      // Store token and user
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(user));
      
      storeLogin(access_token, user);
      addNotification({ message: 'Login successful', type: 'success' });
      return true;
    } catch (error) {
      console.error('Login error:', error);
      addNotification({ message: 'Login failed', type: 'error' });
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: RegisterData) => {
    setIsLoading(true);
    try {
      await authService.register(data);
      addNotification({ message: 'Registration successful, you can now log in', type: 'success' });
      return true;
    } catch (error) {
      console.error('Registration error:', error);
      addNotification({ message: 'Registration failed', type: 'error' });
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('apiKey');
    storeLogout();
    addNotification({ message: 'You have been logged out', type: 'info' });
  };

  const createApiKey = async (name: string) => {
    setIsLoading(true);
    try {
      const response = await authService.createApiKey(name);
      const { key } = response;
      
      localStorage.setItem('apiKey', key);
      setApiKey(key);
      
      addNotification({ message: 'API key created successfully', type: 'success' });
      return key;
    } catch (error) {
      console.error('API key creation error:', error);
      addNotification({ message: 'Failed to create API key', type: 'error' });
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    user,
    token,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    createApiKey
  };
}