import React from "react";
import {createRoot} from "react-dom/client";
import {MotionConfig} from "framer-motion";
import {App} from "./App";
import "./style.css";

function fitViewport() {
  const height = Math.round(window.visualViewport?.height || window.innerHeight || document.documentElement.clientHeight);
  if (height > 0) {
    document.documentElement.style.setProperty("--app-h", `${height}px`);
    document.documentElement.style.height = `${height}px`;
  }
  document.documentElement.classList.toggle("short", height > 0 && height < 560);
}

fitViewport();
window.addEventListener("resize", fitViewport);
window.visualViewport?.addEventListener("resize", fitViewport);
document.addEventListener("visibilitychange", fitViewport);
setTimeout(fitViewport, 120);
setTimeout(fitViewport, 600);

createRoot(document.getElementById("root")!).render(<MotionConfig reducedMotion="user"><App/></MotionConfig>);
