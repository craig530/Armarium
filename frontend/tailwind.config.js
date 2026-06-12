/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Leather-brown ramp anchored on the Armarium logo brown (#7B4A2E ≈ 600).
        brand: {
          50: '#FAF1E9',
          100: '#F3E2D2',
          200: '#E6C7AD',
          300: '#D5A579',
          400: '#C0824F',
          500: '#9C633A',
          600: '#7B4A2E',
          700: '#623A24',
          800: '#4A2C1B',
          900: '#34201A',
          950: '#1E110A',
        },
        // Warm parchment-to-ink neutral ramp, replacing the default cold greys.
        gray: {
          50: '#FAF5EC',
          100: '#F1E6D6',
          200: '#E4D3BC',
          300: '#CBB394',
          400: '#A8896A',
          500: '#8A6F56',
          600: '#6B5642',
          700: '#4F3F30',
          800: '#382C22',
          900: '#211913',
          950: '#15100C',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        serif: ['Fraunces', 'Georgia', 'serif'],
        display: ['Fraunces', 'Georgia', 'serif'],
      },
      keyframes: {
        'scan-sweep': {
          '0%, 100%': { top: '0%' },
          '50%': { top: '100%' },
        },
      },
      animation: {
        'scan-sweep': 'scan-sweep 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
