import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import HomePage from '../pages/HomePage';
import AuthPage from '../pages/AuthPage';
import DashboardPage from '../pages/DashboardPage';
import InferencePage from '../pages/InferencePage';
import TranscriptionPage from '../pages/TranscriptionPage';
import VideoPage from '../pages/VideoPage';
import AccountPage from '../pages/AccountPage';
import BillingPage from '../pages/BillingPage';
import NotFoundPage from '../pages/NotFoundPage';
import PrivateRoute from './PrivateRoute';

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { path: '/', element: <HomePage /> },
      { path: '/auth', element: <AuthPage /> },
      { 
        path: '/dashboard', 
        element: <PrivateRoute><DashboardPage /></PrivateRoute> 
      },
      { 
        path: '/inference', 
        element: <PrivateRoute><InferencePage /></PrivateRoute> 
      },
      { 
        path: '/transcription', 
        element: <PrivateRoute><TranscriptionPage /></PrivateRoute> 
      },
      { 
        path: '/video', 
        element: <PrivateRoute><VideoPage /></PrivateRoute> 
      },
      { 
        path: '/account', 
        element: <PrivateRoute><AccountPage /></PrivateRoute> 
      },
      { 
        path: '/billing', 
        element: <PrivateRoute><BillingPage /></PrivateRoute> 
      },
      { path: '*', element: <NotFoundPage /> }
    ]
  }
]);

export default function AppRouter() {
  return <RouterProvider router={router} />;
}