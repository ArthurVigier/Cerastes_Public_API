import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="text-center py-16">
      <h1 className="text-6xl font-bold text-gray-900 dark:text-white">404</h1>
      <p className="text-xl mt-4 mb-8 text-gray-600 dark:text-gray-300">Page not found</p>
      <Link to="/" className="btn btn-primary">
        Return to Home
      </Link>
    </div>
  );
}