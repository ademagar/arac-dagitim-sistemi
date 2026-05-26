/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        sidebar: '#0F172A',
        'sidebar-hover': '#1E293B',
        primary: '#3B82F6',
        surface: '#F8FAFC',
      },
    },
  },
  plugins: [],
}
