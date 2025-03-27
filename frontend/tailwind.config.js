/** @type {import('tailwindcss').Config} */
module.exports = {
    content: ["./src/**/*.{js,jsx,ts,tsx}"],
    darkMode: 'class',
    theme: {
      extend: {
        colors: {
          primary: {
            50: '#f0f9ff',
            100: '#e0f2fe',
            500: '#0ea5e9',
            600: '#0284c7',
            700: '#0369a1',
          },
          secondary: {
            500: '#8b5cf6',
            600: '#7c3aed',
          },
          dark: {
            700: '#374151',
            800: '#1f2937',
            900: '#111827',
          }
        },
      },
    },
    plugins: [],
  }