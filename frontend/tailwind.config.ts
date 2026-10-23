import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Cherry Blossom Surfaces
        blossom: {
          100: "#F2C7C7", // Surface for cards, table headers, sidebar highlight
          300: "#FFB7C5", // Primary accent, active nav indicator, key highlights
          400: "#F08CA2",
          500: "#E0557D",
          600: "#C2456B", // Primary action buttons (passes WCAG AA against white)
          700: "#9E3256", // Hover/pressed action buttons
        },
        // Mint Surfaces (Success)
        mint: {
          100: "#D5F3D8", // Success surfaces, "on track" chips
          400: "#4ADE80",
          500: "#22C55E",
          700: "#26693D", // Success text/icons on mint-100 (passes 5.5:1 AA)
        },
        // Warning Surfaces (Approaching deadline)
        amberState: {
          100: "#FFF1D6", // Surface
          700: "#8A5A00", // Text/icons on amberState-100
        },
        // Critical / Overdue Surfaces
        roseState: {
          100: "#FFE0E3", // Surface
          700: "#A3213A", // Text/icons on roseState-100
        },
        // Ink Wash Neutrals & Text
        ink: {
          DEFAULT: "#4A4A4A", // Primary body text, headings, table cells
          strong: "#2E2E2E",  // Page titles, KPI numbers
          muted: "#55687C",   // Small captions, helper text (ONLY on white/ivory)
          slate: "#6D8196",   // Secondary large text >=18px or 14px bold, chart lines
          line: "#CBCBCB",    // Borders, dividers, disabled controls (NEVER text)
          ivory: "#FFFFE3",   // Text on dark elements, alternate warm surface
          white: "#FFFFFF",   // Pure surface
        },
        ivory: "#FFFFE3",
      },
      fontFamily: {
        sans: ["'Plus Jakarta Sans'", "'Inter'", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
      },
      borderRadius: {
        xl: "12px",
      },
      boxShadow: {
        soft: "0 2px 8px rgba(74, 74, 74, 0.05)",
        card: "0 4px 16px rgba(74, 74, 74, 0.08)",
        highlight: "0 0 0 2px rgba(194, 69, 107, 0.2)",
      },
    },
  },
  plugins: [],
};

export default config;
