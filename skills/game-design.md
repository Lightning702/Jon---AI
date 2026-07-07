# Spiele-Design (HTML, 2D & 3D)

Anleitung, wie Jon (oder jede KI) spielbare Spiele baut — 2D auf Canvas oder 3D mit
Three.js. Lies das komplett, bevor du Code schreibst. Bearbeitbar: passe Stil und Regeln an.

## Grundprinzipien

1. **Sofort spielbar.** Liefere standardmäßig **eine einzige `index.html`** mit
   eingebettetem CSS und JS, sodass ein Doppelklick reicht. Öffne sie danach mit `open_url`.
2. **Game-Loop mit `requestAnimationFrame`.** Nutze Delta-Zeit (`dt`), damit das Spiel auf
   jedem Gerät gleich schnell läuft — nie feste Schrittweiten pro Frame.
3. **Klarer Zustand.** Halte den Spielzustand (`state`: running/paused/gameover) und alle
   Objekte in einfachen Objekten/Arrays. Trenne **Update** (Logik) von **Render** (Zeichnen).
4. **Eingabe sauber.** Tastatur über ein `keys`-Set (`keydown`/`keyup`), Maus/Touch über
   Events. Unterstütze Touch, damit es auch auf dem Handy läuft.
5. **Start/Neustart.** Immer ein Startbildschirm und ein „Nochmal"-Weg nach Game Over.
6. **Punkte & Feedback.** Score anzeigen, kleine Effekte (Aufblitzen, Partikel) für Wucht.

## 2D-Gerüst (Canvas)

```html
<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Spiel</title>
<style>html,body{margin:0;height:100%;background:#0b0b0f;overflow:hidden}
canvas{display:block;margin:auto;background:#12121a;touch-action:none}</style></head>
<body><canvas id="c" width="480" height="720"></canvas>
<script>
const cv=document.getElementById("c"), ctx=cv.getContext("2d");
const keys=new Set();
addEventListener("keydown",e=>keys.add(e.key));
addEventListener("keyup",e=>keys.delete(e.key));
let state="start", score=0, last=0;
const player={x:240,y:640,w:40,h:40,vx:0};
function reset(){score=0;player.x=240;state="play";}
function update(dt){
  if(state!=="play")return;
  if(keys.has("ArrowLeft"))player.x-=300*dt;
  if(keys.has("ArrowRight"))player.x+=300*dt;
  player.x=Math.max(0,Math.min(cv.width-player.w,player.x));
}
function render(){
  ctx.clearRect(0,0,cv.width,cv.height);
  ctx.fillStyle="#e5b53a";ctx.fillRect(player.x,player.y,player.w,player.h);
  ctx.fillStyle="#fff";ctx.font="20px system-ui";ctx.fillText("Score "+score,12,28);
  if(state!=="play"){ctx.fillStyle="rgba(0,0,0,.6)";ctx.fillRect(0,0,cv.width,cv.height);
    ctx.fillStyle="#fff";ctx.textAlign="center";
    ctx.fillText(state==="start"?"Klick zum Start":"Game Over — Klick",cv.width/2,cv.height/2);
    ctx.textAlign="left";}
}
function loop(t){const dt=Math.min(.05,(t-last)/1000);last=t;update(dt);render();requestAnimationFrame(loop);}
addEventListener("pointerdown",()=>{if(state!=="play")reset();});
requestAnimationFrame(loop);
</script></body></html>
```

Baue das Spiel auf diesem Gerüst aus: Gegner/Hindernisse als Array, Kollision per
Rechteck-Überlappung (AABB), Score hochzählen, Schwierigkeit langsam steigern.

## 3D-Gerüst (Three.js)

Three.js per CDN einbinden (Internet nötig). Grundszene:

```html
<script type="module">
import * as THREE from "https://unpkg.com/three@0.160.0/build/three.module.js";
const scene=new THREE.Scene();
const cam=new THREE.PerspectiveCamera(70,innerWidth/innerHeight,.1,100);
cam.position.z=5;
const r=new THREE.WebGLRenderer({antialias:true});
r.setSize(innerWidth,innerHeight);document.body.appendChild(r.domElement);
scene.add(new THREE.HemisphereLight(0xffffff,0x222233,1));
const cube=new THREE.Mesh(new THREE.BoxGeometry(),new THREE.MeshStandardMaterial({color:0xe5b53a}));
scene.add(cube);
addEventListener("resize",()=>{cam.aspect=innerWidth/innerHeight;cam.updateProjectionMatrix();r.setSize(innerWidth,innerHeight);});
let last=0;
function loop(t){const dt=(t-last)/1000;last=t;cube.rotation.y+=dt;r.render(scene,cam);requestAnimationFrame(loop);}
requestAnimationFrame(loop);
</script>
```

Für echte Spiele: Steuerung (Tastatur/Maus/Pointer-Lock), Kollisionen über
Bounding-Boxes (`THREE.Box3`), Gegner/Physik in `update(dt)`, HUD als HTML-Overlay.

## Vorgehen für Jon

1. Kläre in einem Satz: Genre (Jump'n'Run, Runner, Shooter, Puzzle …), 2D oder 3D.
2. Wähle das passende Gerüst oben.
3. Schreibe die vollständige `index.html` mit `write_file`.
4. Öffne sie mit `open_url` (Dateipfad), damit der Nutzer sofort spielen kann.
5. Frag nach Wünschen (mehr Level, Sound, Gegner) und ändere gezielt mit `edit_file`.

## Checkliste

- [ ] Startbildschirm und Neustart vorhanden
- [ ] Delta-Zeit-basierter Game-Loop
- [ ] Tastatur **und** Touch/Maus funktionieren
- [ ] Score/Feedback sichtbar
- [ ] Läuft flüssig, keine Fehler in der Konsole
- [ ] 3D nur, wenn Internet für die Three.js-CDN da ist; sonst 2D-Canvas
