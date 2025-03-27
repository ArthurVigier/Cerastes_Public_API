import { create } from 'zustand';

interface Notification {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
}

interface UIState {
  isDarkMode: boolean;
  notifications: Notification[];
  toggleDarkMode: () => void;
  addNotification: (notification: Omit<Notification, 'id'>) => void;
  removeNotification: (id: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
  isDarkMode: localStorage.getItem('darkMode') === 'true',
  notifications: [],
  toggleDarkMode: () => 
    set((state) => {
      const newDarkMode = !state.isDarkMode;
      localStorage.setItem('darkMode', String(newDarkMode));
      return { isDarkMode: newDarkMode };
    }),
  addNotification: (notification) => 
    set((state) => ({
      notifications: [
        ...state.notifications, 
        { ...notification, id: Date.now().toString() }
      ]
    })),
  removeNotification: (id) => 
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id)
    })),
}));