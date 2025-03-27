import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function HomePage() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="py-12">
      <div className="text-center">
        <h1 className="text-4xl font-extrabold text-gray-900 dark:text-white sm:text-5xl sm:tracking-tight lg:text-6xl">
          Advanced Content Analysis with Cerastes
        </h1>
        <p className="mt-6 max-w-2xl mx-auto text-xl text-gray-500 dark:text-gray-300">
          An intuitive platform for text analysis, audio transcription, and video analysis
          powered by artificial intelligence.
        </p>
        <div className="mt-10 flex justify-center">
          {isAuthenticated ? (
            <Link
              to="/dashboard"
              className="px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 md:py-4 md:text-lg md:px-10"
            >
              Go to my dashboard
            </Link>
          ) : (
            <Link
              to="/auth"
              className="px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 md:py-4 md:text-lg md:px-10"
            >
              Get started for free
            </Link>
          )}
        </div>
      </div>

      {/* Features */}
      <div className="mt-20">
        <h2 className="text-3xl font-extrabold text-center text-gray-900 dark:text-white">
          Discover our features
        </h2>
        <div className="mt-12 grid gap-8 md:grid-cols-3">
          <div className="card">
            <h3 className="text-xl font-bold mb-2">Text Analysis</h3>
            <p className="text-gray-600 dark:text-gray-300">
              Analyze your text in depth with our advanced AI engine.
            </p>
          </div>
          <div className="card">
            <h3 className="text-xl font-bold mb-2">Audio Transcription</h3>
            <p className="text-gray-600 dark:text-gray-300">
              Convert your audio files to text with exceptional accuracy.
            </p>
          </div>
          <div className="card">
            <h3 className="text-xl font-bold mb-2">Video Analysis</h3>
            <p className="text-gray-600 dark:text-gray-300">
              Extract valuable insights from your video content with our cutting-edge technology.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}