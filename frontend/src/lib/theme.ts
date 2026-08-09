export type Theme = "dark" | "light" | "cozy";

export function istTheme(wert: unknown): wert is Theme {
  return wert === "dark" || wert === "light" || wert === "cozy";
}

export function readTheme(): Theme {
  const gespeichert = localStorage.getItem("jon_theme");
  return istTheme(gespeichert) ? gespeichert : "dark";
}

export function applyTheme(theme: Theme): void {
  const wurzel = document.documentElement;
  wurzel.classList.toggle("light", theme !== "dark");
  wurzel.classList.toggle("cozy", theme === "cozy");
}
