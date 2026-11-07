import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#05060a",
          900: "#0a0c14",
          800: "#11141f",
          700: "#1a1f2e",
          600: "#262c3d",
        },
        brand: {
          50: "#eef7ff",
          200: "#b8e0ff",
          400: "#5ab8ff",
          500: "#2f9bff",
          600: "#0b7ae0",
          700: "#0a5fb0",
        },
        accent: {
          400: "#a78bfa",
          500: "#8b5cf6",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        glow: "0 0 40px -12px rgba(47, 155, 255, 0.45)",
        panel: "0 20px 60px -30px rgba(0, 0, 0, 0.9)",
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg,#2f9bff 0%,#8b5cf6 100%)",
      },
    },
  },
  plugins: [],
};

export default config;
