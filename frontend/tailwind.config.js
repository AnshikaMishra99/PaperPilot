/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#F3F5F1',
        surface: '#FFFFFF',
        ink: '#161D1A',
        muted: '#5E6B64',
        line: '#DDE2DA',
        pine: {
          50: '#EDF3EF',
          100: '#D6E4DA',
          500: '#2C6250',
          600: '#1F4D3D',
          700: '#163A2E',
        },
        ochre: '#8A6D2F',
        flag: '#9B3A2F',
      },
      fontFamily: {
        read: ['Newsreader', 'Georgia', 'serif'],
        ui: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
      },
      maxWidth: {
        reading: '68ch',
      },
    },
  },
  plugins: [],
}
