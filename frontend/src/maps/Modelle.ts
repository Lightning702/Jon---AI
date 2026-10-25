import { Mesh, Modell, Vec3, buildPlane } from "./PlaneLayer";

export type Fortbewegung = "fuss" | "auto" | "flugzeug";

export interface ModellArt {
  id: string;
  name: string;
  art: Fortbewegung;
  von: number;
  bis: number;
  laenge: number;
  bauen: (farbe: Vec3, zeit: number) => Modell;
  animiert?: boolean;
}

export const FARBEN: { name: string; wert: Vec3 }[] = [
  { name: "Gold", wert: [0.83, 0.69, 0.22] },
  { name: "Rot", wert: [0.72, 0.1, 0.12] },
  { name: "Blau", wert: [0.12, 0.27, 0.62] },
  { name: "Grün", wert: [0.13, 0.42, 0.26] },
  { name: "Schwarz", wert: [0.07, 0.07, 0.08] },
  { name: "Weiß", wert: [0.92, 0.92, 0.9] },
  { name: "Silber", wert: [0.66, 0.68, 0.71] },
  { name: "Creme", wert: [0.88, 0.82, 0.66] },
  { name: "Orange", wert: [0.9, 0.45, 0.1] },
  { name: "Türkis", wert: [0.1, 0.55, 0.58] },
];

const SCHWARZ: Vec3 = [0.05, 0.05, 0.06];
const REIFEN: Vec3 = [0.08, 0.08, 0.09];
const FELGE: Vec3 = [0.72, 0.74, 0.77];
const GLAS: Vec3 = [0.1, 0.15, 0.22];
const CHROM: Vec3 = [0.8, 0.82, 0.86];
const LICHT: Vec3 = [1, 0.96, 0.82];
const RUECKLICHT: Vec3 = [0.75, 0.05, 0.06];
const MESSING: Vec3 = [0.72, 0.56, 0.24];
const HOLZ: Vec3 = [0.45, 0.3, 0.17];
const STOFF: Vec3 = [0.86, 0.82, 0.72];
const HAUT: Vec3 = [0.87, 0.68, 0.55];
const HOSE: Vec3 = [0.14, 0.18, 0.3];
const SCHUH: Vec3 = [0.12, 0.09, 0.07];
const HAAR: Vec3 = [0.22, 0.14, 0.08];
const WEISS: Vec3 = [0.93, 0.94, 0.96];
const GRAU: Vec3 = [0.55, 0.57, 0.6];

function dunkler(farbe: Vec3, faktor: number): Vec3 {
  return [farbe[0] * faktor, farbe[1] * faktor, farbe[2] * faktor];
}

function hexa(mesh: Mesh, p: Vec3[], farbe: Vec3, oben: Vec3 = farbe): void {
  const [a, b, c, d, e, f, g, h] = p;
  mesh.quad(d, c, b, a, dunkler(farbe, 0.7));
  mesh.quad(e, f, g, h, oben);
  mesh.quad(a, b, f, e, farbe);
  mesh.quad(b, c, g, f, farbe);
  mesh.quad(c, d, h, g, farbe);
  mesh.quad(d, a, e, h, farbe);
}

function kasten(
  mesh: Mesh,
  x: [number, number],
  y: [number, number],
  z: [number, number],
  farbe: Vec3,
  oben?: Vec3,
  dreh?: (p: Vec3) => Vec3
): void {
  const punkte: Vec3[] = [
    [x[0], y[0], z[0]],
    [x[1], y[0], z[0]],
    [x[1], y[1], z[0]],
    [x[0], y[1], z[0]],
    [x[0], y[0], z[1]],
    [x[1], y[0], z[1]],
    [x[1], y[1], z[1]],
    [x[0], y[1], z[1]],
  ];
  hexa(mesh, dreh ? punkte.map(dreh) : punkte, farbe, oben ?? farbe);
}

function trapez(
  mesh: Mesh,
  unten: { x: number; y: [number, number]; z: number },
  oben: { x: number; y: [number, number]; z: number },
  farbe: Vec3,
  deckel?: Vec3
): void {
  hexa(
    mesh,
    [
      [-unten.x, unten.y[0], unten.z],
      [unten.x, unten.y[0], unten.z],
      [unten.x, unten.y[1], unten.z],
      [-unten.x, unten.y[1], unten.z],
      [-oben.x, oben.y[0], oben.z],
      [oben.x, oben.y[0], oben.z],
      [oben.x, oben.y[1], oben.z],
      [-oben.x, oben.y[1], oben.z],
    ],
    farbe,
    deckel ?? farbe
  );
}

function rad(mesh: Mesh, x: number, y: number, radius: number, breite: number, felge: Vec3 = FELGE, speichen = false): void {
  const teile = 14;
  const innen = x > 0 ? x - breite / 2 : x + breite / 2;
  const aussen = x > 0 ? x + breite / 2 : x - breite / 2;
  const punkt = (winkel: number, r: number, seite: number): Vec3 => [seite, y + Math.cos(winkel) * r, radius + Math.sin(winkel) * r];
  for (let i = 0; i < teile; i += 1) {
    const a = (i / teile) * Math.PI * 2;
    const b = ((i + 1) / teile) * Math.PI * 2;
    mesh.quad(punkt(a, radius, innen), punkt(b, radius, innen), punkt(b, radius, aussen), punkt(a, radius, aussen), REIFEN);
    const mitte: Vec3 = [aussen, y, radius];
    mesh.tri(mitte, punkt(a, radius * 0.62, aussen), punkt(b, radius * 0.62, aussen), felge);
    mesh.quad(punkt(a, radius * 0.62, aussen), punkt(b, radius * 0.62, aussen), punkt(b, radius, aussen), punkt(a, radius, aussen), REIFEN);
    mesh.tri([innen, y, radius], punkt(b, radius, innen), punkt(a, radius, innen), REIFEN);
  }
  if (speichen) {
    for (let i = 0; i < 6; i += 1) {
      const w = (i / 6) * Math.PI;
      const dx = Math.cos(w) * radius * 0.9;
      const dz = Math.sin(w) * radius * 0.9;
      const s = aussen + (x > 0 ? 0.01 : -0.01);
      mesh.quad([s, y - dx - 0.02, radius - dz], [s, y - dx + 0.02, radius - dz], [s, y + dx + 0.02, radius + dz], [s, y + dx - 0.02, radius + dz], felge);
    }
  }
}

function ellipsoid(mesh: Mesh, mitte: Vec3, r: Vec3, farbe: Vec3, segmente = 12, ringe = 7, unten = -1): void {
  const punkt = (u: number, v: number): Vec3 => {
    const theta = (u / segmente) * Math.PI * 2;
    const phi = -Math.PI / 2 + (v / ringe) * Math.PI;
    return [
      mitte[0] + Math.cos(phi) * Math.sin(theta) * r[0],
      mitte[1] + Math.cos(phi) * Math.cos(theta) * r[1],
      mitte[2] + Math.max(unten, Math.sin(phi)) * r[2],
    ];
  };
  for (let v = 0; v < ringe; v += 1) {
    for (let u = 0; u < segmente; u += 1) {
      mesh.quad(punkt(u, v), punkt(u + 1, v), punkt(u + 1, v + 1), punkt(u, v + 1), farbe);
    }
  }
}

function lichter(mesh: Mesh, breite: number, vorn: number, hinten: number, hoehe: number, rund = false): void {
  for (const seite of [-1, 1]) {
    const x = seite * breite;
    if (rund) {
      ellipsoid(mesh, [x, vorn, hoehe], [0.11, 0.06, 0.11], LICHT, 8, 4);
    } else {
      kasten(mesh, [x - 0.17, x + 0.17], [vorn - 0.04, vorn + 0.02], [hoehe - 0.06, hoehe + 0.06], LICHT);
    }
    kasten(mesh, [x - 0.15, x + 0.15], [hinten - 0.02, hinten + 0.04], [hoehe - 0.05, hoehe + 0.06], RUECKLICHT);
  }
}

function limousine(farbe: Vec3): Modell {
  const m = new Mesh();
  trapez(m, { x: 0.9, y: [-2.33, 2.36], z: 0.3 }, { x: 0.88, y: [-2.28, 2.3], z: 0.8 }, farbe);
  trapez(m, { x: 0.88, y: [1.25, 2.3], z: 0.8 }, { x: 0.84, y: [1.3, 2.25], z: 0.86 }, farbe);
  trapez(m, { x: 0.86, y: [-1.45, 1.25], z: 0.8 }, { x: 0.72, y: [-0.95, 0.5], z: 1.42 }, GLAS);
  trapez(m, { x: 0.72, y: [-0.95, 0.5], z: 1.42 }, { x: 0.7, y: [-0.9, 0.45], z: 1.46 }, farbe);
  kasten(m, [-0.89, 0.89], [-0.15, -0.05], [0.84, 1.36], farbe);
  kasten(m, [-0.92, 0.92], [2.3, 2.42], [0.32, 0.52], SCHWARZ);
  kasten(m, [-0.92, 0.92], [-2.4, -2.28], [0.32, 0.52], SCHWARZ);
  kasten(m, [-0.42, 0.42], [2.34, 2.38], [0.55, 0.72], SCHWARZ);
  lichter(m, 0.62, 2.34, -2.34, 0.7);
  for (const x of [-0.82, 0.82]) for (const y of [-1.45, 1.45]) rad(m, x, y, 0.34, 0.24);
  return m.modell();
}

function suv(farbe: Vec3): Modell {
  const m = new Mesh();
  trapez(m, { x: 0.95, y: [-2.3, 2.35], z: 0.42 }, { x: 0.94, y: [-2.28, 2.3], z: 1.05 }, farbe);
  trapez(m, { x: 0.92, y: [-2.15, 1.3], z: 1.05 }, { x: 0.82, y: [-2.05, 0.65], z: 1.72 }, GLAS);
  trapez(m, { x: 0.82, y: [-2.05, 0.65], z: 1.72 }, { x: 0.8, y: [-2.0, 0.6], z: 1.78 }, farbe);
  kasten(m, [-0.93, 0.93], [-0.55, -0.45], [1.07, 1.68], farbe);
  kasten(m, [-0.6, 0.6], [-1.2, 0.2], [1.79, 1.84], GRAU);
  kasten(m, [-0.98, 0.98], [2.3, 2.45], [0.4, 0.66], SCHWARZ);
  kasten(m, [-0.98, 0.98], [-2.42, -2.28], [0.4, 0.66], SCHWARZ);
  kasten(m, [-0.5, 0.5], [2.33, 2.38], [0.72, 0.95], SCHWARZ);
  lichter(m, 0.66, 2.33, -2.32, 0.92);
  for (const x of [-0.86, 0.86]) for (const y of [-1.5, 1.5]) rad(m, x, y, 0.4, 0.28);
  return m.modell();
}

function sportwagen(farbe: Vec3): Modell {
  const m = new Mesh();
  trapez(m, { x: 0.96, y: [-2.25, 2.3], z: 0.22 }, { x: 0.92, y: [-2.2, 2.0], z: 0.68 }, farbe);
  trapez(m, { x: 0.92, y: [1.0, 2.0], z: 0.68 }, { x: 0.86, y: [1.1, 2.3], z: 0.52 }, farbe);
  trapez(m, { x: 0.86, y: [-1.3, 0.95], z: 0.68 }, { x: 0.64, y: [-0.9, 0.05], z: 1.1 }, GLAS);
  trapez(m, { x: 0.64, y: [-0.9, 0.05], z: 1.1 }, { x: 0.62, y: [-0.86, 0.02], z: 1.13 }, farbe);
  kasten(m, [-0.85, 0.85], [-2.3, -2.12], [0.95, 1.0], SCHWARZ);
  kasten(m, [-0.06, 0.06], [-2.2, -2.12], [0.66, 0.96], SCHWARZ);
  kasten(m, [-0.98, 0.98], [-2.3, -2.2], [0.22, 0.4], SCHWARZ);
  lichter(m, 0.66, 2.24, -2.27, 0.56);
  for (const x of [-0.86, 0.86]) for (const y of [-1.4, 1.35]) rad(m, x, y, 0.33, 0.3, CHROM);
  return m.modell();
}

function rundheck(farbe: Vec3): Modell {
  const m = new Mesh();
  kasten(m, [-0.7, 0.7], [-1.8, 1.8], [0.26, 0.5], dunkler(farbe, 0.8));
  ellipsoid(m, [0, 0.05, 0.55], [0.78, 2.0, 0.55], farbe, 14, 8, -0.35);
  ellipsoid(m, [0, -0.2, 0.98], [0.66, 0.95, 0.5], GLAS, 12, 6, -0.2);
  ellipsoid(m, [0, -0.25, 1.06], [0.6, 0.82, 0.45], farbe, 12, 6, 0);
  for (const x of [-0.72, 0.72]) for (const y of [-1.2, 1.25]) ellipsoid(m, [x, y, 0.5], [0.22, 0.48, 0.3], farbe, 10, 5, -0.1);
  kasten(m, [-0.82, 0.82], [2.0, 2.1], [0.36, 0.44], CHROM);
  kasten(m, [-0.82, 0.82], [-2.08, -1.98], [0.36, 0.44], CHROM);
  lichter(m, 0.68, 1.62, -1.95, 0.72, true);
  for (const x of [-0.73, 0.73]) for (const y of [-1.2, 1.25]) rad(m, x, y, 0.32, 0.18);
  return m.modell();
}

function oldtimer(farbe: Vec3): Modell {
  const m = new Mesh();
  kasten(m, [-0.6, 0.6], [-1.75, 1.9], [0.42, 0.55], SCHWARZ);
  kasten(m, [-0.42, 0.42], [0.95, 1.9], [0.55, 1.05], farbe);
  kasten(m, [-0.44, 0.44], [1.9, 1.98], [0.5, 1.12], MESSING);
  kasten(m, [-0.62, 0.62], [-1.55, 0.95], [0.55, 1.12], farbe);
  kasten(m, [-0.62, -0.56], [-0.6, 0.9], [1.12, 1.82], SCHWARZ);
  kasten(m, [0.56, 0.62], [-0.6, 0.9], [1.12, 1.82], SCHWARZ);
  kasten(m, [-0.58, 0.58], [0.88, 0.92], [1.12, 1.62], GLAS);
  kasten(m, [-0.66, 0.66], [-0.7, 0.98], [1.82, 1.88], SCHWARZ);
  kasten(m, [-0.5, 0.5], [-1.4, -0.75], [1.0, 1.15], HOLZ);
  for (const seite of [-1, 1]) {
    kasten(m, seite > 0 ? [0.62, 0.82] : [-0.82, -0.62], [-1.0, 0.9], [0.5, 0.54], SCHWARZ);
    ellipsoid(m, [seite * 0.48, 1.95, 1.05], [0.09, 0.08, 0.09], LICHT, 8, 4);
  }
  for (const x of [-0.7, 0.7]) for (const y of [-1.25, 1.45]) rad(m, x, y, 0.42, 0.1, HOLZ, true);
  return m.modell();
}

function mensch(farbe: Vec3, zeit: number): Modell {
  const m = new Mesh();
  const schwung = Math.sin(zeit) * 0.55;
  const um = (pivot: Vec3, winkel: number) => (p: Vec3): Vec3 => {
    const dy = p[1] - pivot[1];
    const dz = p[2] - pivot[2];
    return [p[0], pivot[1] + dy * Math.cos(winkel) - dz * Math.sin(winkel), pivot[2] + dy * Math.sin(winkel) + dz * Math.cos(winkel)];
  };
  const huefte: Vec3 = [0, 0, 0.92];
  kasten(m, [-0.2, -0.04], [-0.08, 0.08], [0.06, 0.92], HOSE, HOSE, um(huefte, schwung));
  kasten(m, [0.04, 0.2], [-0.08, 0.08], [0.06, 0.92], HOSE, HOSE, um(huefte, -schwung));
  kasten(m, [-0.2, -0.04], [-0.08, 0.17], [0, 0.07], SCHUH, SCHUH, um(huefte, schwung));
  kasten(m, [0.04, 0.2], [-0.08, 0.17], [0, 0.07], SCHUH, SCHUH, um(huefte, -schwung));
  trapez(m, { x: 0.2, y: [-0.11, 0.11], z: 0.9 }, { x: 0.24, y: [-0.12, 0.12], z: 1.48 }, farbe);
  const schulter: Vec3 = [0, 0, 1.44];
  kasten(m, [-0.33, -0.24], [-0.06, 0.06], [0.82, 1.46], farbe, farbe, um(schulter, -schwung * 0.8));
  kasten(m, [0.24, 0.33], [-0.06, 0.06], [0.82, 1.46], farbe, farbe, um(schulter, schwung * 0.8));
  kasten(m, [-0.32, -0.25], [-0.05, 0.05], [0.72, 0.82], HAUT, HAUT, um(schulter, -schwung * 0.8));
  kasten(m, [0.25, 0.32], [-0.05, 0.05], [0.72, 0.82], HAUT, HAUT, um(schulter, schwung * 0.8));
  kasten(m, [-0.05, 0.05], [-0.05, 0.05], [1.48, 1.55], HAUT);
  ellipsoid(m, [0, 0.01, 1.66], [0.11, 0.12, 0.13], HAUT, 10, 6);
  ellipsoid(m, [0, -0.02, 1.72], [0.115, 0.12, 0.09], HAAR, 10, 5, 0);
  return m.modell();
}

function propeller(m: Mesh, y: number, z: number, zeit: number, laenge: number): void {
  const w = zeit * 40;
  for (const versatz of [0, Math.PI]) {
    const a = w + versatz;
    const dx = Math.cos(a) * laenge;
    const dz = Math.sin(a) * laenge;
    const qx = -Math.sin(a) * 0.06;
    const qz = Math.cos(a) * 0.06;
    m.quad([qx, y, z + qz], [dx + qx, y, z + dz + qz], [dx - qx, y, z + dz - qz], [-qx, y, z - qz], SCHWARZ);
  }
  ellipsoid(m, [0, y + 0.08, z], [0.14, 0.2, 0.14], CHROM, 8, 4);
}

function rumpf(m: Mesh, abschnitte: [number, number, number][], farbe: Vec3, unten: Vec3): void {
  const ring = 10;
  const punkte = abschnitte.map(([y, r, z]) => {
    const liste: Vec3[] = [];
    for (let i = 0; i < ring; i += 1) {
      const w = (i / ring) * Math.PI * 2;
      liste.push([Math.sin(w) * r, y, z + Math.cos(w) * r]);
    }
    return liste;
  });
  for (let s = 0; s < punkte.length - 1; s += 1) {
    for (let i = 0; i < ring; i += 1) {
      const n = (i + 1) % ring;
      const oben = Math.cos((i / ring) * Math.PI * 2) > -0.3;
      m.quad(punkte[s][i], punkte[s][n], punkte[s + 1][n], punkte[s + 1][i], oben ? farbe : unten);
    }
  }
  const erster = abschnitte[0];
  const letzter = abschnitte[abschnitte.length - 1];
  for (let i = 0; i < ring; i += 1) {
    const n = (i + 1) % ring;
    m.tri([0, erster[0] - 0.05, erster[2]], punkte[0][n], punkte[0][i], unten);
    m.tri([0, letzter[0] + 0.05, letzter[2]], punkte[punkte.length - 1][i], punkte[punkte.length - 1][n], farbe);
  }
}

function propellermaschine(farbe: Vec3, zeit: number): Modell {
  const m = new Mesh();
  rumpf(m, [[-4.2, 0.12, 1.25], [-2.5, 0.45, 1.15], [-0.4, 0.62, 1.05], [1.2, 0.62, 1.0], [2.2, 0.48, 0.95]], WEISS, dunkler(farbe, 0.9));
  kasten(m, [-0.5, 0.5], [0.0, 1.25], [1.2, 1.72], GLAS);
  kasten(m, [-5.5, 5.5], [0.0, 1.5], [1.72, 1.82], WEISS, farbe);
  kasten(m, [-5.5, -5.1], [0.0, 1.5], [1.7, 1.84], farbe);
  kasten(m, [5.1, 5.5], [0.0, 1.5], [1.7, 1.84], farbe);
  for (const seite of [-1, 1]) {
    hexa(m, [[seite * 0.5, 0.6, 0.8], [seite * 0.56, 0.75, 0.8], [seite * 2.6, 0.95, 1.74], [seite * 2.55, 0.8, 1.74], [seite * 0.5, 0.6, 0.86], [seite * 0.56, 0.75, 0.86], [seite * 2.6, 0.95, 1.78], [seite * 2.55, 0.8, 1.78]], GRAU);
  }
  kasten(m, [-1.8, 1.8], [-4.4, -3.6], [1.18, 1.26], WEISS, farbe);
  hexa(m, [[-0.05, -3.4, 1.3], [0.05, -3.4, 1.3], [0.05, -4.4, 1.3], [-0.05, -4.4, 1.3], [-0.05, -3.9, 2.5], [0.05, -3.9, 2.5], [0.05, -4.55, 2.5], [-0.05, -4.55, 2.5]], farbe);
  for (const x of [-1.1, 1.1]) {
    kasten(m, [x - 0.04, x + 0.04], [0.6, 0.7], [0.3, 0.75], GRAU);
    rad(m, x, 0.65, 0.25, 0.12);
  }
  rad(m, 0.0001, 1.9, 0.18, 0.1);
  propeller(m, 2.3, 0.95, zeit, 0.95);
  return m.modell();
}

function doppeldecker(farbe: Vec3, zeit: number): Modell {
  const m = new Mesh();
  rumpf(m, [[-4.0, 0.1, 1.4], [-2.4, 0.38, 1.3], [-0.6, 0.5, 1.2], [1.0, 0.52, 1.15], [1.9, 0.5, 1.1]], farbe, dunkler(farbe, 0.8));
  kasten(m, [-0.3, 0.3], [-0.6, 0.3], [1.66, 1.72], SCHWARZ);
  kasten(m, [-4.2, 4.2], [0.2, 1.6], [0.72, 0.82], STOFF, farbe);
  kasten(m, [-4.5, 4.5], [0.4, 1.8], [2.3, 2.4], STOFF, farbe);
  for (const x of [-3.4, -1.4, 1.4, 3.4]) {
    kasten(m, [x - 0.04, x + 0.04], [0.55, 0.65], [0.82, 2.3], HOLZ);
    kasten(m, [x - 0.04, x + 0.04], [1.25, 1.35], [0.82, 2.3], HOLZ);
  }
  kasten(m, [-1.5, 1.5], [-4.2, -3.5], [1.32, 1.38], STOFF, farbe);
  hexa(m, [[-0.04, -3.2, 1.4], [0.04, -3.2, 1.4], [0.04, -4.2, 1.4], [-0.04, -4.2, 1.4], [-0.04, -3.7, 2.3], [0.04, -3.7, 2.3], [0.04, -4.3, 2.3], [-0.04, -4.3, 2.3]], farbe);
  for (const x of [-0.8, 0.8]) {
    kasten(m, [x - 0.04, x + 0.04], [0.9, 1.0], [0.38, 0.9], SCHWARZ);
    rad(m, x, 0.95, 0.36, 0.1, STOFF, true);
  }
  propeller(m, 2.0, 1.1, zeit, 1.15);
  return m.modell();
}

function jet(farbe: Vec3): Modell {
  return buildPlane(farbe);
}

export const MODELLE: ModellArt[] = [
  { id: "mensch", name: "Spaziergänger", art: "fuss", von: -5000, bis: 9999, laenge: 0.4, bauen: mensch, animiert: true },
  { id: "oldtimer", name: "Oldtimer", art: "auto", von: 1890, bis: 1938, laenge: 3.9, bauen: (f) => oldtimer(f) },
  { id: "rundheck", name: "Rundheck", art: "auto", von: 1935, bis: 1980, laenge: 4.1, bauen: (f) => rundheck(f) },
  { id: "limousine", name: "Limousine", art: "auto", von: 1975, bis: 9999, laenge: 4.7, bauen: (f) => limousine(f) },
  { id: "suv", name: "SUV", art: "auto", von: 1995, bis: 9999, laenge: 4.7, bauen: (f) => suv(f) },
  { id: "sport", name: "Sportwagen", art: "auto", von: 1960, bis: 9999, laenge: 4.5, bauen: (f) => sportwagen(f) },
  { id: "doppeldecker", name: "Doppeldecker", art: "flugzeug", von: 1903, bis: 1940, laenge: 8.5, bauen: doppeldecker, animiert: true },
  { id: "propeller", name: "Propellermaschine", art: "flugzeug", von: 1930, bis: 9999, laenge: 8.5, bauen: propellermaschine, animiert: true },
  { id: "jet", name: "Verkehrsjet", art: "flugzeug", von: 1958, bis: 9999, laenge: 33, bauen: (f) => jet(f) },
];

export function modellFuer(art: Fortbewegung, jahr: number): ModellArt {
  const passend = MODELLE.filter((m) => m.art === art && m.von <= jahr && jahr <= m.bis);
  const liste = passend.length ? passend : MODELLE.filter((m) => m.art === art);
  return liste.sort((a, b) => b.von - a.von).find((m) => m.id !== "sport" && m.id !== "suv") ?? liste[0];
}

export function modellById(id: string): ModellArt | undefined {
  return MODELLE.find((m) => m.id === id);
}
