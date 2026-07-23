import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#18202f",
        field: "#eef2f7",
        signal: "#1f9d8a",
        risk: "#d94862",
        steel: "#556070",
        cloud: "#f7f9fc"
      },
      boxShadow: {
        panel: "0 1px 2px rgba(24, 32, 47, 0.08)"
      }
    }
  },
  plugins: []
} satisfies Config;

