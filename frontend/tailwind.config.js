/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        surface: {
          50: '#f8fafc',
          100: '#1e1b2e',
          200: '#171525',
          300: '#13111f',
          400: '#0e0d18',
          500: '#0a0912',
        },
        accent: {
          DEFAULT: '#7c5cfc',
          light: '#a78bfa',
          glow: '#6d4aff',
          muted: '#5b3fd6',
        },
        emerald: {
          glow: '#34d399',
        },
        amber: {
          glow: '#fbbf24',
        },
        rose: {
          glow: '#fb7185',
        },
      },
      boxShadow: {
        glow: '0 0 20px rgba(124, 92, 252, 0.3)',
        'glow-lg': '0 0 40px rgba(124, 92, 252, 0.4)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.6s ease-out',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
    },
  },
  plugins: [],
};
