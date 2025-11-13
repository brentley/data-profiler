/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'vq-primary': '#116df8',
        'vq-accent': '#ff5100',
      },
    },
  },
  plugins: [],
}
