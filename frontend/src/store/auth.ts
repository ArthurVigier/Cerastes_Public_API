import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  username: string;
  email: string;
}

interface AuthState {
  token: string | null;
  apiKey: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  setApiKey: (apiKey: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      apiKey: null,
      user: null,
      isAuthenticated: false,
      login: (token, user) => set({ token, user, isAuthenticated: true }),
      setApiKey: (apiKey) => set({ apiKey }),
      logout: () => set({ token: null, user: null, apiKey: null, isAuthenticated: false }),
    }),
    {
      name: 'auth-storage',
    }
  )
);