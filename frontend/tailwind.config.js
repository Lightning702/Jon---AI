/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        white: "rgb(var(--weiss-rgb) / <alpha-value>)",
        gold: {
          DEFAULT: "rgb(var(--gold-rgb) / <alpha-value>)",
          light: "rgb(var(--gold-light-rgb) / <alpha-value>)",
          dark: "rgb(var(--gold-dark-rgb) / <alpha-value>)",
        },
        ink: {
          900: "#050506",
          800: "#0b0b0f",
          700: "#121218",
          600: "#1a1a22",
        },
      },
      fontFamily: {
        sans: ["var(--jd-schrift, Inter)", "system-ui", "sans-serif"],
      },
      borderRadius: {
        sm: "calc(0.125rem * var(--jd-rund, 1))",
        DEFAULT: "calc(0.25rem * var(--jd-rund, 1))",
        md: "calc(0.375rem * var(--jd-rund, 1))",
        lg: "calc(0.5rem * var(--jd-rund, 1))",
        xl: "calc(0.75rem * var(--jd-rund, 1))",
        "2xl": "calc(1rem * var(--jd-rund, 1))",
        "3xl": "calc(1.5rem * var(--jd-rund, 1))",
      },
      backdropBlur: {
        xs: "2px",
      },
      boxShadow: {
        glass: "0 8px 32px rgba(0,0,0,0.55)",
        gold: "0 0 24px rgb(var(--gold-rgb) / 0.25)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        shimmer: "shimmer 2.5s linear infinite",
      },
    },
  },
  plugins: [],
};
