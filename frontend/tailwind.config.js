/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: "#060913",
          card: "rgba(13, 20, 38, 0.6)",
          border: "rgba(32, 45, 83, 0.4)",
          cyan: "#00f0ff",
          magenta: "#ff007f",
          green: "#39ff14",
          yellow: "#ffd700",
          gray: "#8f9bb3"
        }
      },
      boxShadow: {
        'glow-cyan': '0 0 15px rgba(0, 240, 255, 0.35)',
        'glow-magenta': '0 0 15px rgba(255, 0, 127, 0.35)',
        'glow-green': '0 0 15px rgba(57, 255, 20, 0.35)',
      }
    },
  },
  plugins: [],
}
