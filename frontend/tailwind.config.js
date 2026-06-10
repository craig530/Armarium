/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f4ff',
          100: '#dde6ff',
          200: '#c4d1ff',
          300: '#9cb1ff',
          400: '#7086ff',
          500: '#4f5eff',
          600: '#3a3df5',
          700: '#2f2fd8',
          800: '#2828ae',
          900: '#262889',
          950: '#161651',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
