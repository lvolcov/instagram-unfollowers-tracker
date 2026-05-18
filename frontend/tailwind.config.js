/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Match the original tool's dark aesthetic
        background: "#111111",
        surface: "#1c1c1e",
        "surface-hover": "#2c2c2e",
        primary: "#007aff",
        "primary-hover": "#0051d5",
        danger: "#ff3b30",
        success: "#34c759",
        muted: "#8e8e93",
        border: "rgba(255,255,255,0.08)",
      },
    },
  },
  plugins: [],
};
