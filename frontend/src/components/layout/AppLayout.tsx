import { Outlet } from 'react-router-dom';
import Header from './Header';
import Footer from './Footer';
import { NotificationContainer } from '../ui/Notification';
import { useUIStore } from '../../store/ui';
import { useEffect } from 'react';

export default function AppLayout() {
  const isDarkMode = useUIStore((state) => state.isDarkMode);
  
  useEffect(() => {
    // Apply dark mode to HTML document
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
      <Footer />
      <NotificationContainer />
    </div>
  );
}