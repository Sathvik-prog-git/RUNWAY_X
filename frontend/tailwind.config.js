/** Design tokens taken from the RUNWAY X dashboard reference screenshot. */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: { 950: "#030917", 900: "#050d22", 800: "#081634", 700: "#0c2250", 600: "#123070" },
        brand: { cyan: "#22d3ee", blue: "#3b82f6", sky: "#38bdf8", violet: "#8b5cf6", teal: "#14b8a6" },
        good: "#10d9a0",
        bad: "#f43f5e",
        warn: "#fbbf24",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "Roboto", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(56,189,248,0.25), 0 0 24px -6px rgba(37,99,235,0.55)",
        "glow-sm": "0 0 14px -4px rgba(56,189,248,0.5)",
      },
      backgroundImage: {
        "app-bg":
          "radial-gradient(1200px 500px at 85% -10%, rgba(37,99,235,0.28), transparent 60%), linear-gradient(180deg,#040b1f 0%,#030917 100%)",
        "card-bg": "linear-gradient(160deg, rgba(14,40,92,0.55) 0%, rgba(5,13,34,0.85) 70%)",
        "nav-active": "linear-gradient(90deg, #1d4ed8 0%, #0ea5e9 100%)",
      },
    },
  },
  plugins: [],
};
