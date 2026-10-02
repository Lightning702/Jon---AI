import React from "react";
import {createRoot} from "react-dom/client";
import MediaPanel from "../src/components/MediaPanel";
import "../src/index.css";
const job = {id: "preview", kind: "transcribe", title: "Besprechung.mp3", status: "done", progress: 100, message: "Fertig", preview: "Am Sonntag gibt es Schnitzel zum Mittagessen.\nWir treffen uns um zwölf Uhr.", summary: "Für Sonntag ist Schnitzel zum Mittagessen um zwölf Uhr geplant.", files: ["transkript.txt"]};
window.fetch = async input => {
  const url = String(input);
  return new Response(JSON.stringify(url.endsWith("/jobs") ? [job] : job), {status:200,headers:{"Content-Type":"application/json"}});
};
createRoot(document.getElementById("root")!).render(<MediaPanel onClose={() => {}} uploads={[{id:"uploaded",name:"Besprechung.mp3"}]}/>);
