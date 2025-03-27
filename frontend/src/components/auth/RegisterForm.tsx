import { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import Button from '../ui/Button';

export default function RegisterForm({ onToggleForm }: { onToggleForm: () => void }) {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { register, isLoading } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await register({ username, email, password });
    if (success) {
      onToggleForm(); // Redirect to login form
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="username" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Username
        </label>
        <input
          id="username"
          type="text"
          required
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="mt-1 input focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-900"
        />
      </div>
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Email
        </label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 input focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-900"
        />
      </div>
      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Password
        </label>
        <input
          id="password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 input focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-900"
        />
      </div>
      <div>
        <Button type="submit" isLoading={isLoading} className="w-full">
          Sign up
        </Button>
      </div>
      <div className="text-center mt-4">
        <button
          type="button"
          onClick={onToggleForm}
          className="text-sm text-primary-600 hover:text-primary-500 dark:text-primary-400"
        >
          Already have an account? Sign in
        </button>
      </div>
    </form>
  );
}