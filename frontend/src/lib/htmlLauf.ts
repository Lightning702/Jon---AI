import { useEffect, useState } from "react";

export const LAUF_SANDBOX = "allow-scripts allow-modals allow-pointer-lock allow-forms allow-popups";

const HELFER = `(function(){var k=document.currentScript&&document.currentScript.getAttribute("data-k");function text(t){if(t instanceof Error)return t.stack||String(t);if(t&&typeof t==="object"){try{return JSON.stringify(t)}catch(e){return String(t)}}return String(t)}function senden(art,teile){try{parent.postMessage({jonLauf:k,art:art,text:teile.map(text).join(" ").slice(0,2000)},"*")}catch(e){}}["log","info","warn","error","debug"].forEach(function(n){var alt=console[n];console[n]=function(){senden(n,[].slice.call(arguments));return alt.apply(console,arguments)}});addEventListener("error",function(e){senden("error",[(e.message||"Fehler")+(e.lineno?" (Zeile "+e.lineno+")":"")])});addEventListener("unhandledrejection",function(e){var r=e.reason;senden("error",["Promise: "+(r&&r.message||r)])});try{localStorage.getItem("_")}catch(e){var m={};var s={getItem:function(x){return Object.prototype.hasOwnProperty.call(m,x)?m[x]:null},setItem:function(x,v){m[x]=String(v)},removeItem:function(x){delete m[x]},clear:function(){m={}},key:function(i){return Object.keys(m)[i]||null},get length(){return Object.keys(m).length}};try{Object.defineProperty(window,"localStorage",{value:s,configurable:true});Object.defineProperty(window,"sessionStorage",{value:s,configurable:true})}catch(f){}}})();`;

export function laufSeite(code: string, sprache: string, kennung: string): string {
  const art = sprache.toLowerCase();
  const seite = art === "svg" ? `<!doctype html><html><head></head><body style="margin:0;display:grid;place-items:center;min-height:100vh;background:#fff">${code}</body></html>` : code;
  const einschub = `<script data-k="${kennung}">${HELFER}</script>`;
  for (const muster of [/<head(\s[^>]*)?>/i, /<html(\s[^>]*)?>/i, /<!doctype[^>]*>/i]) {
    const treffer = muster.exec(seite);
    if (treffer) {
      const ende = treffer.index + treffer[0].length;
      return seite.slice(0, ende) + einschub + seite.slice(ende);
    }
  }
  return einschub + seite;
}

export function sprachePfad(pfad: string): string {
  const endung = /\.([a-z0-9]+)$/i.exec(pfad)?.[1]?.toLowerCase() || "";
  const namen: Record<string, string> = { htm: "html", mjs: "js", cjs: "js" };
  return namen[endung] || endung;
}

export function useVerzoegert<T>(wert: T, ms: number): T {
  const [verzoegert, setVerzoegert] = useState(wert);
  useEffect(() => {
    const zeit = window.setTimeout(() => setVerzoegert(wert), ms);
    return () => window.clearTimeout(zeit);
  }, [wert, ms]);
  return verzoegert;
}

export function nutzerCode(text: string): { text: string; bloecke: { sprache: string; code: string }[] } {
  const bloecke: { sprache: string; code: string }[] = [];
  const rest = text.replace(/```([\w+-]*)[^\n]*\n([\s\S]*?)```/g, (_, sprache: string, code: string) => {
    bloecke.push({ sprache: (sprache || "text").toLowerCase(), code: code.replace(/\n$/, "") });
    return "";
  });
  if (bloecke.length) return { text: rest.replace(/\n{3,}/g, "\n\n").trim(), bloecke };
  const start = text.search(/<!doctype\s+html|<html[\s>]/i);
  if (start >= 0 && /<\/(html|body|script|div|canvas|svg)>/i.test(text.slice(start))) {
    return { text: text.slice(0, start).trim(), bloecke: [{ sprache: "html", code: text.slice(start).trim() }] };
  }
  return { text, bloecke };
}
