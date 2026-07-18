import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

if (localStorage.getItem("jon_theme") === "light") {
  document.documentElement.classList.add("light");
}

const rawFetch = window.fetch.bind(window);
window.fetch = async (
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> => {
  const url =
    typeof input === "string"
      ? input
      : input instanceof URL
        ? input.href
        : input.url;
  const isApi = url.includes("/api/") && !url.includes("/api/pair/");
  if (isApi) {
    const token = localStorage.getItem("jon_device_token");
    if (token) {
      const headers = new Headers(init?.headers ?? {});
      headers.set("X-Jon-Token", token);
      init = { ...(init ?? {}), headers };
    }
  }
  const response = await rawFetch(input as RequestInfo, init);
  if (isApi && response.status === 401) {
    try {
      const body = await response.clone().json();
      if (body?.detail === "pairing_required") {
        window.dispatchEvent(new CustomEvent("jon:pairing-required"));
      }
    } catch {
      void 0;
    }
  }
  return response;
};

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
