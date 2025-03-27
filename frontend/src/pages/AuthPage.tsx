import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import LoginForm from '../components/auth/LoginForm';
import RegisterForm from '../components/auth/RegisterForm';
import Card from '../components/ui/Card';

export default function AuthPage() {
  const [isLoginForm, setIsLoginForm] = useState(true);
  const { isAuthenticated } = useAuth();

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="flex justify-center items-center py-12">
      <Card className="max-w-md w-full">
        <h2 className="text-2xl font-semibold text-center mb-6">
          {isLoginForm ? 'Sign In' : 'Create Account'}
        </h2>
        {isLoginForm ? (
          <LoginForm onToggleForm={() => setIsLoginForm(false)} />
        ) : (
          <RegisterForm onToggleForm={() => setIsLoginForm(true)} />
        )}
      </Card>
    </div>
  );
}