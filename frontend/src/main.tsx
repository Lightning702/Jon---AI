import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import { applyTheme, readTheme } from "./lib/theme";
import { installTokenFetch, resolveToken } from "./lib/token";

resolveToken();
installTokenFetch();
applyTheme(readTheme());

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
