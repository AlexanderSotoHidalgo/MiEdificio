/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#17211b',
        forest: '#174c3a',
        mint: '#dff3e8',
        paper: '#f7f7f2',
        coral: '#ef795f',
      },
      boxShadow: {
        soft: '0 16px 50px rgba(23, 76, 58, 0.10)',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
      },
    },
  },
  plugins: [],
}

