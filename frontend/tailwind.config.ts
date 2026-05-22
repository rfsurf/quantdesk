import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Horizon UI brand (purple → blue)
        brand: {
          50: "#E9E3FF",
          100: "#C9C1FF",
          200: "#A794FF",
          300: "#868CFF",
          400: "#7551FF",
          500: "#422AFB",
          600: "#3100EC",
          700: "#2600B8",
          800: "#1D0085",
          900: "#150052",
        },
        // Navy dark background system
        navy: {
          50: "#F4F7FE",
          100: "#E6EBFA",
          200: "#C6D2EA",
          300: "#9FB3D6",
          400: "#6B8AAB",
          500: "#3D5A80",
          600: "#2D4A70",
          700: "#1B254B",
          800: "#111c44",
          900: "#0b1437",
        },
        // Horizon UI gray
        gray: {
          50: "#F4F7FE",
          100: "#E6EBFA",
          200: "#C6D2EA",
          300: "#AAAAAA",
          400: "#999999",
          500: "#777777",
          600: "#666666",
          700: "#555555",
          800: "#333333",
          900: "#111111",
        },
        // Financial
        profit: "#22c55e",
        loss: "#ef4444",
        // Semantic
        lightPrimary: "#F4F7FE",
        darkPrimary: "#0b1437",
      },
      borderRadius: {
        "2xl": "20px",
        "3xl": "24px",
        "4xl": "30px",
      },
      boxShadow: {
        // Horizon UI shadow scale
        soft: "0px 2px 14px 0px rgba(112, 144, 176, 0.08)",
        card: "0px 2px 8px rgba(112, 144, 176, 0.12)",
        "card-hover": "0px 6px 20px rgba(112, 144, 176, 0.18)",
        "dark-soft": "0px 2px 14px 0px rgba(0, 0, 0, 0.25)",
        "dark-card": "0px 2px 8px rgba(0, 0, 0, 0.35)",
        "dark-hover": "0px 6px 20px rgba(0, 0, 0, 0.45)",
        // Glassmorphism
        glass: "0px 8px 32px rgba(112, 144, 176, 0.15)",
        "glass-dark": "0px 8px 32px rgba(0, 0, 0, 0.3)",
        // Elevated
        elevated: "0px 18px 40px rgba(112, 144, 176, 0.2)",
        "elevated-dark": "0px 18px 40px rgba(0, 0, 0, 0.5)",
        // Brand glow
        "brand-glow": "0px 0px 20px rgba(67, 24, 255, 0.25)",
        "brand-glow-sm": "0px 0px 10px rgba(67, 24, 255, 0.15)",
      },
      backgroundImage: {
        // Brand gradients
        "brand-gradient": "linear-gradient(310deg, #422AFB 0%, #868CFF 100%)",
        "brand-gradient-alt": "linear-gradient(135deg, #4318FF 0%, #868CFF 100%)",
        "brand-gradient-radial": "radial-gradient(circle, #868CFF 0%, #422AFB 100%)",
        // Navy gradients
        "navy-gradient": "linear-gradient(180deg, #1B254B 0%, #111c44 100%)",
        "navy-gradient-radial": "radial-gradient(circle, #111c44 0%, #0b1437 100%)",
        // Hero
        "hero-gradient": "linear-gradient(135deg, #F4F7FE 0%, #E9E3FF 50%, #C9C1FF 100%)",
        "hero-gradient-dark": "linear-gradient(135deg, #111c44 0%, #1B254B 50%, #2600B8 100%)",
        // Glass
        "glass-light": "linear-gradient(135deg, rgba(255,255,255,0.7) 0%, rgba(255,255,255,0.4) 100%)",
        "glass-dark": "linear-gradient(135deg, rgba(27,37,75,0.7) 0%, rgba(17,28,68,0.4) 100%)",
        // Card subtle
        "card-gradient": "linear-gradient(180deg, #FFFFFF 0%, #F4F7FE 100%)",
        "card-gradient-dark": "linear-gradient(180deg, #1B254B 0%, #111c44 100%)",
      },
      backdropBlur: {
        card: "16px",
        nav: "20px",
        modal: "24px",
      },
      transitionDuration: {
        "350": "350ms",
        "400": "400ms",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(20px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "slide-in-right": {
          "0%": { opacity: "0", transform: "translateX(20px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.95)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        pulse: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.35s ease-out forwards",
        "fade-in-up": "fade-in-up 0.5s ease-out forwards",
        "slide-in-right": "slide-in-right 0.35s ease-out forwards",
        "scale-in": "scale-in 0.3s ease-out forwards",
        shimmer: "shimmer 2s linear infinite",
        "pulse-slow": "pulse 3s ease-in-out infinite",
      },
      fontFamily: {
        sans: [
          "DM Sans",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
