import React from "react";
import ReactDOM from "react-dom/client";
import { MotionConfig } from "framer-motion";
import App from "./App";
import Anmeldung from "./components/Anmeldung";
import DesignHintergrund from "./components/DesignHintergrund";
import ErrorBoundary from "./components/ErrorBoundary";
import WeicheSchreibmarke from "./components/WeicheSchreibmarke";
import "./index.css";
import { applyTheme, readTheme } from "./lib/theme";
import { designStarten } from "./lib/design";
import { herzenStarten } from "./lib/herzen";
import { installTokenFetch, resolveToken } from "./lib/token";

resolveToken();
installTokenFetch();
applyTheme(readTheme());
designStarten();
herzenStarten();

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <MotionConfig reducedMotion="user">
      <ErrorBoundary>
        <DesignHintergrund />
        <Anmeldung>
          <App />
        </Anmeldung>
        <WeicheSchreibmarke />
      </ErrorBoundary>
    </MotionConfig>
  </React.StrictMode>
);
