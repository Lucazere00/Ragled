import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0f1720",
        coal: "#111518",
        panel: "#171c21",
        line: "#2b333b",
        signal: "#54d6a8",
        amber: "#f4bd50"
      },
      boxShadow: {
        glow: "0 20px 70px rgba(84, 214, 168, 0.12)"
      }
    }
  },
  plugins: []
};

export default config;
