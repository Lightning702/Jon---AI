const $ = id => document.getElementById(id);
const PERSONAS = {
  jon: {name: "Jon", unter: "Dein KI-Assistent von FelWorks", gruss: "Hallo, ich bin Jon. Frag mich etwas, lass dir etwas erklären oder schreiben.", platzhalter: "Schreib Jon etwas …", vorschlaege: ["Was kannst du alles?", "Erklär mir Photosynthese in drei Sätzen", "Plan mir einen perfekten Tag in Wien", "Schreib eine kurze Geburtstagsnachricht"]},
  minijon: {name: "MiniJon", unter: "Jons kleiner, verspielter Begleiter", gruss: "Hey, ich bin MiniJon! 👋 Klein, aber schlau. Was liegt an?", platzhalter: "Schreib MiniJon etwas …", vorschlaege: ["Erzähl mir einen Witz", "Gib mir einen Motivationsspruch", "Was soll ich heute kochen?", "Wer bist du eigentlich?"]},
};
const ZUSTAND = {basis: "", modus: "jon", verlaeufe: {jon: [], minijon: []}, laeuft: false, routeModus: "auto"};

function status(text, zustand) {
  const el = $("status");
  el.dataset.zustand = zustand;
  el.lastElementChild.textContent = text;
  $("status-klein").textContent = zustand === "an" ? "Online" : zustand === "aus" ? "Offline" : "Verbinde …";
}

async function verbinden() {
  try {
    const adresse = await (await fetch("/.netlify/functions/demo-adresse", {cache: "no-store"})).json();
    ZUSTAND.basis = (adresse.url || "").replace(/\/$/, "");
    if (!ZUSTAND.basis) throw new Error();
    const antwort = await fetch(ZUSTAND.basis + "/demo/status", {signal: AbortSignal.timeout(9000)});
    if (!antwort.ok) throw new Error();
    status("Jon ist online", "an");
  } catch {
    status("Die Demo ist gerade offline. Schau bald wieder vorbei.", "aus");
  }
  pruefen();
}

function escape(text) {
  return text.replace(/[&<>"']/g, z => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[z]));
}

function inline(text) {
  return text
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
}

function markdown(text) {
  return escape(text).split(/```/).map((teil, i) => {
    if (i % 2) return `<pre><code>${teil.replace(/^[a-z0-9]*\n/i, "")}</code></pre>`;
    const html = [];
    let liste = null;
    let absatz = [];
    const absatzEnde = () => {if (absatz.length) html.push(`<p>${absatz.join("<br>")}</p>`); absatz = [];};
    const listeEnde = () => {if (liste) html.push(`<${liste.art}>${liste.punkte.map(p => `<li>${p}</li>`).join("")}</${liste.art}>`); liste = null;};
    for (const zeile of teil.split("\n")) {
      const punkt = zeile.match(/^\s*([-*•]|\d+[.)])\s+(.*)$/);
      if (punkt) {
        absatzEnde();
        const art = /\d/.test(punkt[1]) ? "ol" : "ul";
        if (liste && liste.art !== art) listeEnde();
        if (!liste) liste = {art, punkte: []};
        liste.punkte.push(inline(punkt[2]));
      } else if (zeile.trim()) {
        listeEnde();
        absatz.push(inline(zeile.replace(/^#{1,6}\s*/, "")));
      } else {
        listeEnde();
        absatzEnde();
      }
    }
    listeEnde();
    absatzEnde();
    return html.join("");
  }).join("");
}

function amEnde() {
  const v = $("verlauf");
  return v.scrollHeight - v.scrollTop - v.clientHeight < 120;
}

function nachUnten(erzwingen = false) {
  const v = $("verlauf");
  if (erzwingen || amEnde()) requestAnimationFrame(() => {v.scrollTop = v.scrollHeight;});
}

function avatar(wer) {
  const el = document.createElement("span");
  el.className = "tv-avatar" + (wer === "minijon" ? " tv-avatar--mini" : "");
  el.innerHTML = '<svg viewBox="0 0 120 120"><use href="#jon-face"/></svg>';
  return el;
}

function nachricht(wer, html, art = "") {
  const zeile = document.createElement("div");
  zeile.className = `tv-nachricht tv-nachricht--${wer === "du" ? "du" : ZUSTAND.modus}${art ? " tv-nachricht--" + art : ""}`;
  const blase = document.createElement("div");
  blase.className = "tv-blase";
  if (wer === "du") blase.textContent = html;
  else blase.innerHTML = html;
  if (wer !== "du") zeile.appendChild(avatar(ZUSTAND.modus));
  zeile.appendChild(blase);
  $("verlauf").appendChild(zeile);
  return blase;
}

function vorschlaege() {
  const box = $("vorschlaege");
  box.innerHTML = "";
  if (ZUSTAND.verlaeufe[ZUSTAND.modus].length) return;
  PERSONAS[ZUSTAND.modus].vorschlaege.forEach((text, i) => {
    const knopf = document.createElement("button");
    knopf.type = "button";
    knopf.textContent = text;
    knopf.style.animationDelay = i * 40 + "ms";
    knopf.addEventListener("click", () => senden(text));
    box.appendChild(knopf);
  });
}

function chatZeigen() {
  const p = PERSONAS[ZUSTAND.modus];
  $("chat-name").textContent = p.name;
  $("chat-unter").textContent = p.unter;
  $("chat-avatar").className = "tv-avatar" + (ZUSTAND.modus === "minijon" ? " tv-avatar--mini" : "");
  $("text").placeholder = p.platzhalter;
  $("verlauf").innerHTML = "";
  nachricht("bot", `<p>${escape(p.gruss)}</p>`);
  for (const n of ZUSTAND.verlaeufe[ZUSTAND.modus]) {
    if (n.role === "user") nachricht("du", n.content);
    else nachricht("bot", markdown(n.content));
  }
  vorschlaege();
  nachUnten(true);
}

function pruefen() {
  const text = $("text").value;
  $("senden").disabled = ZUSTAND.laeuft || !text.trim() || !ZUSTAND.basis;
  $("zaehler").textContent = text.length > 1200 ? `${text.length}/1500` : "";
}

function wachsen() {
  const feld = $("text");
  feld.style.height = "auto";
  feld.style.height = Math.min(feld.scrollHeight, 160) + "px";
}

async function senden(vorgabe) {
  const text = (vorgabe ?? $("text").value).trim();
  if (!text || ZUSTAND.laeuft || !ZUSTAND.basis) return;
  const persona = ZUSTAND.modus;
  const verlauf = ZUSTAND.verlaeufe[persona];
  verlauf.push({role: "user", content: text});
  $("vorschlaege").innerHTML = "";
  nachricht("du", text);
  $("text").value = "";
  wachsen();
  ZUSTAND.laeuft = true;
  pruefen();
  const blase = nachricht("bot", '<span class="tv-tippt" aria-label="Jon schreibt"><i></i><i></i><i></i></span>');
  nachUnten(true);
  let inhalt = "";
  let bild = 0;
  const zeichnen = () => {bild = 0; if (ZUSTAND.modus === persona) {blase.innerHTML = markdown(inhalt); nachUnten();}};
  try {
    const antwort = await fetch(ZUSTAND.basis + "/demo/chat", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({persona, nachrichten: verlauf.slice(-12)})});
    if (!antwort.ok) {
      const daten = await antwort.json().catch(() => ({}));
      throw new Error(typeof daten.detail === "string" ? daten.detail : "Jon antwortet gerade nicht.");
    }
    const leser = antwort.body.getReader();
    const decoder = new TextDecoder();
    let puffer = "";
    for (;;) {
      const {value, done} = await leser.read();
      if (done) break;
      puffer += decoder.decode(value, {stream: true});
      const stuecke = puffer.split("\n\n");
      puffer = stuecke.pop();
      for (const stueck of stuecke) {
        if (!stueck.startsWith("data: ")) continue;
        const daten = JSON.parse(stueck.slice(6));
        if (daten.fehler) throw new Error(daten.fehler);
        if (daten.delta) {inhalt += daten.delta; if (!bild) bild = requestAnimationFrame(zeichnen);}
      }
    }
    if (bild) cancelAnimationFrame(bild);
    zeichnen();
    verlauf.push({role: "assistant", content: inhalt || "…"});
  } catch (fehler) {
    verlauf.pop();
    blase.parentElement.classList.add("tv-nachricht--fehler");
    blase.innerHTML = `<p>${escape(fehler.message || "Jon antwortet gerade nicht.")}</p>`;
  } finally {
    ZUSTAND.laeuft = false;
    pruefen();
    if (matchMedia("(pointer:fine)").matches) $("text").focus();
  }
}

function modusWechseln(modus) {
  ZUSTAND.modus = modus === "minijon" ? "minijon" : modus === "jon" ? "jon" : ZUSTAND.modus;
  document.querySelectorAll(".tv-modi [role=tab]").forEach(tab => tab.setAttribute("aria-selected", String(tab.dataset.modus === modus)));
  const panel = modus === "maps" ? "panel-maps" : modus === "transkript" ? "panel-transkript" : "panel-chat";
  document.querySelectorAll(".tv-panel").forEach(p => {p.hidden = p.id !== panel;});
  if (panel === "panel-chat") chatZeigen();
}

function treffer(liste) {
  const box = $("kartenergebnis");
  box.innerHTML = "";
  liste.forEach((ort, i) => {
    const knopf = document.createElement("button");
    knopf.type = "button";
    knopf.className = "tv-ort" + (i === 0 ? " an" : "");
    knopf.style.animationDelay = i * 40 + "ms";
    knopf.innerHTML = '<svg><use href="#t-map"/></svg><span><b></b><small></small></span>';
    knopf.querySelector("b").textContent = ort.name || "Ort";
    knopf.querySelector("small").textContent = ort.label || "";
    knopf.addEventListener("click", () => {box.querySelectorAll(".tv-ort").forEach(k => k.classList.toggle("an", k === knopf)); karte(ort.lat, ort.lon);});
    box.appendChild(knopf);
  });
}

function kartenFehler(text) {
  $("kartenergebnis").innerHTML = '<p class="tv-fehler"></p>';
  $("kartenergebnis").firstChild.textContent = text;
}

function karte(lat, lon, d = 0.012) {
  const rahmen = $("karte");
  rahmen.src = `https://www.openstreetmap.org/export/embed.html?bbox=${lon - d},${lat - d},${lon + d},${lat + d}&layer=mapnik&marker=${lat},${lon}`;
  rahmen.hidden = false;
  $("karte-leer").hidden = true;
}

async function ortSuchen(event) {
  event.preventDefault();
  const q = $("ort").value.trim();
  if (q.length < 2 || !ZUSTAND.basis) return;
  $("kartenergebnis").innerHTML = '<p class="tv-leer">Suche …</p>';
  try {
    const antwort = await fetch(ZUSTAND.basis + "/demo/orte?q=" + encodeURIComponent(q));
    const daten = await antwort.json();
    if (!antwort.ok) throw new Error(daten.detail || "Die Suche hat nicht geklappt.");
    if (!daten.treffer.length) {kartenFehler("Dazu habe ich nichts gefunden. Versuch es mit einem anderen Namen."); return;}
    treffer(daten.treffer.slice(0, 6));
    karte(daten.treffer[0].lat, daten.treffer[0].lon);
  } catch (fehler) {
    kartenFehler(fehler.message || "Die Suche hat nicht geklappt.");
  }
}

async function routeBerechnen(event) {
  event.preventDefault();
  const von = $("von").value.trim();
  const nach = $("nach").value.trim();
  if (von.length < 2 || nach.length < 2 || !ZUSTAND.basis) return;
  $("kartenergebnis").innerHTML = '<p class="tv-leer">Berechne die Route …</p>';
  try {
    const antwort = await fetch(ZUSTAND.basis + "/demo/route", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({von, nach, modus: ZUSTAND.routeModus})});
    const daten = await antwort.json();
    if (!antwort.ok) throw new Error(daten.detail || "Die Route ließ sich nicht berechnen.");
    const km = (daten.route.distance_m || 0) / 1000;
    const minuten = Math.max(1, Math.round((daten.route.duration_s || 0) / 60));
    const dauer = minuten >= 60 ? `${Math.floor(minuten / 60)} Std. ${minuten % 60} Min.` : `${minuten} Min.`;
    const karteHtml = document.createElement("div");
    karteHtml.className = "tv-route-karte";
    karteHtml.innerHTML = "<strong></strong><span></span><small></small>";
    karteHtml.querySelector("strong").textContent = dauer;
    karteHtml.querySelector("span").textContent = `${km.toFixed(km < 10 ? 1 : 0)} km · ${{auto: "mit dem Auto", fahrrad: "mit dem Rad", fuss: "zu Fuß"}[ZUSTAND.routeModus]}`;
    karteHtml.querySelector("small").textContent = `${daten.von.label || daten.von.name} → ${daten.nach.label || daten.nach.name}`;
    $("kartenergebnis").innerHTML = "";
    $("kartenergebnis").appendChild(karteHtml);
    const abstand = Math.max(Math.abs(daten.von.lat - daten.nach.lat), Math.abs(daten.von.lon - daten.nach.lon)) * 0.65 + 0.01;
    karte((daten.von.lat + daten.nach.lat) / 2, (daten.von.lon + daten.nach.lon) / 2, abstand);
  } catch (fehler) {
    kartenFehler(fehler.message || "Die Route ließ sich nicht berechnen.");
  }
}

function wav(puffer) {
  const rate = 16000;
  const kanal = puffer.getChannelData(0);
  const schritt = puffer.sampleRate / rate;
  const laenge = Math.floor(kanal.length / schritt);
  const daten = new DataView(new ArrayBuffer(44 + laenge * 2));
  const schreiben = (o, t) => [...t].forEach((c, i) => daten.setUint8(o + i, c.charCodeAt(0)));
  schreiben(0, "RIFF"); daten.setUint32(4, 36 + laenge * 2, true); schreiben(8, "WAVE"); schreiben(12, "fmt ");
  daten.setUint32(16, 16, true); daten.setUint16(20, 1, true); daten.setUint16(22, 1, true); daten.setUint32(24, rate, true);
  daten.setUint32(28, rate * 2, true); daten.setUint16(32, 2, true); daten.setUint16(34, 16, true); schreiben(36, "data"); daten.setUint32(40, laenge * 2, true);
  for (let i = 0; i < laenge; i++) daten.setInt16(44 + i * 2, Math.max(-1, Math.min(1, kanal[Math.floor(i * schritt)])) * 0x7fff, true);
  return new Blob([daten], {type: "audio/wav"});
}

function ergebnis(text, fehler = false) {
  $("transkript-ergebnis").hidden = false;
  $("transkripttext").textContent = text;
  $("transkripttext").style.color = fehler ? "#f6c4be" : "";
  $("kopieren").hidden = fehler;
}

async function transkribieren(blob) {
  if (!ZUSTAND.basis) return ergebnis("Die Demo ist gerade offline.", true);
  ergebnis("Jon hört zu …");
  $("kopieren").hidden = true;
  try {
    const kontext = new AudioContext();
    const puffer = await kontext.decodeAudioData(await blob.arrayBuffer());
    void kontext.close();
    if (puffer.duration > 61) throw new Error("In der Demo bitte höchstens eine Minute.");
    const antwort = await fetch(ZUSTAND.basis + "/demo/transkript", {method: "POST", headers: {"Content-Type": "audio/wav"}, body: wav(puffer)});
    const daten = await antwort.json();
    if (!antwort.ok) throw new Error(daten.detail || "Die Transkription hat nicht geklappt.");
    ergebnis(daten.text || "Ich habe leider nichts verstanden.");
  } catch (fehler) {
    ergebnis(fehler.message || "Diese Aufnahme ließ sich nicht lesen.", true);
  }
}

const AUFNAHME = {rekorder: null, strom: null, kontext: null, analyse: null, bild: 0, start: 0};

function pegelZeichnen() {
  const leinwand = $("pegel");
  const stift = leinwand.getContext("2d");
  const breite = leinwand.width = leinwand.clientWidth * devicePixelRatio;
  const hoehe = leinwand.height = leinwand.clientHeight * devicePixelRatio;
  const werte = new Uint8Array(AUFNAHME.analyse ? AUFNAHME.analyse.frequencyBinCount : 0);
  const balken = 48;
  const schleife = () => {
    stift.clearRect(0, 0, breite, hoehe);
    if (AUFNAHME.analyse) AUFNAHME.analyse.getByteFrequencyData(werte);
    const verlauf = stift.createLinearGradient(0, 0, breite, 0);
    verlauf.addColorStop(0, "#f5d67b");
    verlauf.addColorStop(1, "#b8901f");
    stift.fillStyle = verlauf;
    const b = breite / balken;
    for (let i = 0; i < balken; i++) {
      const wert = werte.length ? werte[Math.floor(i * werte.length / balken / 2)] / 255 : 0;
      const h = Math.max(3 * devicePixelRatio, wert * hoehe * .9);
      stift.globalAlpha = .35 + wert * .65;
      stift.fillRect(i * b + b * .2, (hoehe - h) / 2, b * .6, h);
    }
    stift.globalAlpha = 1;
    if (!AUFNAHME.rekorder) return;
    const sekunden = Math.round((Date.now() - AUFNAHME.start) / 1000);
    $("aufnahme-zeit").textContent = `${sekunden} s · tippe zum Beenden`;
    if (sekunden >= 60) AUFNAHME.rekorder.stop();
    else AUFNAHME.bild = requestAnimationFrame(schleife);
  };
  schleife();
}

async function aufnehmen() {
  if (AUFNAHME.rekorder) {AUFNAHME.rekorder.stop(); return;}
  try {
    AUFNAHME.strom = await navigator.mediaDevices.getUserMedia({audio: true});
  } catch {
    ergebnis("Ohne Mikrofon-Freigabe geht es nicht. Du kannst stattdessen eine Audiodatei wählen.", true);
    return;
  }
  const stuecke = [];
  AUFNAHME.kontext = new AudioContext();
  AUFNAHME.analyse = AUFNAHME.kontext.createAnalyser();
  AUFNAHME.analyse.fftSize = 256;
  AUFNAHME.kontext.createMediaStreamSource(AUFNAHME.strom).connect(AUFNAHME.analyse);
  AUFNAHME.rekorder = new MediaRecorder(AUFNAHME.strom);
  AUFNAHME.rekorder.ondataavailable = e => stuecke.push(e.data);
  AUFNAHME.rekorder.onstop = () => {
    cancelAnimationFrame(AUFNAHME.bild);
    AUFNAHME.strom.getTracks().forEach(t => t.stop());
    void AUFNAHME.kontext.close();
    AUFNAHME.rekorder = null;
    AUFNAHME.analyse = null;
    $("aufnehmen").classList.remove("an");
    $("aufnehmen").setAttribute("aria-label", "Aufnahme starten");
    $("aufnahme-titel").textContent = "Tippe zum Aufnehmen";
    $("aufnahme-zeit").textContent = "Bis zu 60 Sekunden, Jon wandelt es in Text um.";
    pegelZeichnen();
    void transkribieren(new Blob(stuecke, {type: stuecke[0]?.type || "audio/webm"}));
  };
  AUFNAHME.rekorder.start();
  AUFNAHME.start = Date.now();
  $("aufnehmen").classList.add("an");
  $("aufnehmen").setAttribute("aria-label", "Aufnahme beenden");
  $("aufnahme-titel").textContent = "Jon hört zu …";
  pegelZeichnen();
}

document.querySelectorAll(".tv-modi [role=tab]").forEach(tab => tab.addEventListener("click", () => modusWechseln(tab.dataset.modus)));
$("chatform").addEventListener("submit", e => {e.preventDefault(); void senden();});
$("text").addEventListener("input", () => {wachsen(); pruefen();});
$("text").addEventListener("keydown", e => {if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {e.preventDefault(); void senden();}});
$("neu").addEventListener("click", () => {if (ZUSTAND.laeuft) return; ZUSTAND.verlaeufe[ZUSTAND.modus] = []; chatZeigen();});
$("ortform").addEventListener("submit", ortSuchen);
$("routeform").addEventListener("submit", routeBerechnen);
document.querySelectorAll(".tv-segment button").forEach(knopf => knopf.addEventListener("click", () => {
  ZUSTAND.routeModus = knopf.dataset.modus;
  document.querySelectorAll(".tv-segment button").forEach(k => k.setAttribute("aria-checked", String(k === knopf)));
}));
$("aufnehmen").addEventListener("click", () => void aufnehmen());
$("datei").addEventListener("change", e => {const datei = e.target.files[0]; if (datei) void transkribieren(datei); e.target.value = "";});
const drop = $("drop");
["dragenter", "dragover"].forEach(art => drop.addEventListener(art, e => {e.preventDefault(); drop.classList.add("ueber");}));
["dragleave", "drop"].forEach(art => drop.addEventListener(art, e => {e.preventDefault(); drop.classList.remove("ueber");}));
drop.addEventListener("drop", e => {const datei = e.dataTransfer.files[0]; if (datei) void transkribieren(datei);});
$("kopieren").addEventListener("click", async () => {
  try {await navigator.clipboard.writeText($("transkripttext").textContent);} catch {return;}
  $("kopieren").lastElementChild.textContent = "Kopiert";
  setTimeout(() => {$("kopieren").lastElementChild.textContent = "Kopieren";}, 1800);
});

chatZeigen();
pegelZeichnen();
verbinden();
