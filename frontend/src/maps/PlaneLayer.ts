import type maplibregl from "maplibre-gl";

export interface PlanePose {
  lon: number;
  lat: number;
  altitude: number;
  heading: number;
  pitch: number;
  roll: number;
  visible: boolean;
  scale: number;
}

type Vec3 = [number, number, number];

class Mesh {
  positions: number[] = [];
  normals: number[] = [];
  colors: number[] = [];

  tri(a: Vec3, b: Vec3, c: Vec3, color: Vec3): void {
    const ux = b[0] - a[0];
    const uy = b[1] - a[1];
    const uz = b[2] - a[2];
    const vx = c[0] - a[0];
    const vy = c[1] - a[1];
    const vz = c[2] - a[2];
    let nx = uy * vz - uz * vy;
    let ny = uz * vx - ux * vz;
    let nz = ux * vy - uy * vx;
    const length = Math.hypot(nx, ny, nz) || 1;
    nx /= length;
    ny /= length;
    nz /= length;
    [a, b, c].forEach((point) => {
      this.positions.push(point[0], point[1], point[2]);
      this.normals.push(nx, ny, nz);
      this.colors.push(color[0], color[1], color[2]);
    });
  }

  quad(a: Vec3, b: Vec3, c: Vec3, d: Vec3, color: Vec3): void {
    this.tri(a, b, c, color);
    this.tri(a, c, d, color);
  }

  slab(
    corners: Vec3[],
    axis: number,
    thickness: number,
    color: Vec3,
    edge: Vec3
  ): void {
    const half = thickness / 2;
    const move = (point: Vec3, delta: number): Vec3 => {
      const copy: Vec3 = [point[0], point[1], point[2]];
      copy[axis] += delta;
      return copy;
    };
    const front = corners.map((point) => move(point, half));
    const back = corners.map((point) => move(point, -half));
    this.quad(front[0], front[1], front[2], front[3], color);
    this.quad(back[3], back[2], back[1], back[0], edge);
    for (let index = 0; index < 4; index += 1) {
      const next = (index + 1) % 4;
      this.quad(back[index], front[index], front[next], back[next], edge);
    }
  }
}

const WHITE: Vec3 = [0.93, 0.94, 0.96];
const SHADE: Vec3 = [0.68, 0.71, 0.76];
const GOLD: Vec3 = [0.83, 0.69, 0.22];
const DARK: Vec3 = [0.16, 0.17, 0.21];
const GLASS: Vec3 = [0.08, 0.12, 0.2];
const METAL: Vec3 = [0.4, 0.42, 0.47];

const SECTIONS: [number, number, number][] = [
  [-15.4, 0.3, 0.95],
  [-12.6, 1.05, 0.6],
  [-8.0, 1.6, 0.2],
  [-2.0, 1.9, 0.0],
  [4.5, 1.9, 0.0],
  [9.5, 1.72, 0.12],
  [13.4, 1.24, 0.34],
  [15.6, 0.55, 0.5],
];

const RING = 10;

function ringPoints(y: number, radius: number, lift: number): Vec3[] {
  const points: Vec3[] = [];
  for (let index = 0; index < RING; index += 1) {
    const angle = (index / RING) * Math.PI * 2;
    points.push([
      Math.sin(angle) * radius,
      y,
      lift + Math.cos(angle) * radius * 0.94,
    ]);
  }
  return points;
}

function bodyColor(index: number): Vec3 {
  const angle = (index / RING) * Math.PI * 2;
  const up = Math.cos(angle);
  if (up > 0.45) return WHITE;
  if (up < -0.55) return SHADE;
  return GOLD;
}

function mirrored(corners: Vec3[]): Vec3[] {
  return corners.map((point) => [-point[0], point[1], point[2]] as Vec3).reverse();
}

function tube(
  mesh: Mesh,
  x: number,
  z: number,
  back: number,
  front: number,
  radius: number
): void {
  const rear = ringPoints(back, radius, 0).map(
    (point) => [point[0] + x, point[1], point[2] + z] as Vec3
  );
  const nose = ringPoints(front, radius, 0).map(
    (point) => [point[0] + x, point[1], point[2] + z] as Vec3
  );
  for (let index = 0; index < RING; index += 1) {
    const next = (index + 1) % RING;
    mesh.quad(rear[index], rear[next], nose[next], nose[index], METAL);
  }
  const intake: Vec3 = [x, front + 0.2, z];
  const exhaust: Vec3 = [x, back - 0.3, z];
  for (let index = 0; index < RING; index += 1) {
    const next = (index + 1) % RING;
    mesh.tri(intake, nose[index], nose[next], DARK);
    mesh.tri(exhaust, rear[next], rear[index], DARK);
  }
}

export function buildPlane(): {
  positions: Float32Array;
  normals: Float32Array;
  colors: Float32Array;
  count: number;
} {
  const mesh = new Mesh();
  const rings = SECTIONS.map(([y, radius, lift]) => ringPoints(y, radius, lift));
  for (let section = 0; section < rings.length - 1; section += 1) {
    const back = rings[section];
    const front = rings[section + 1];
    for (let index = 0; index < RING; index += 1) {
      const next = (index + 1) % RING;
      mesh.quad(
        back[index],
        back[next],
        front[next],
        front[index],
        bodyColor(index)
      );
    }
  }
  const nose: Vec3 = [0, 17.1, 0.55];
  const tail: Vec3 = [0, -16.3, 1.05];
  const first = rings[0];
  const last = rings[rings.length - 1];
  for (let index = 0; index < RING; index += 1) {
    const next = (index + 1) % RING;
    mesh.tri(nose, last[index], last[next], WHITE);
    mesh.tri(tail, first[next], first[index], SHADE);
  }

  mesh.quad(
    [-1.25, 12.4, 1.5],
    [1.25, 12.4, 1.5],
    [1.05, 14.6, 1.05],
    [-1.05, 14.6, 1.05],
    GLASS
  );

  const wing: Vec3[] = [
    [1.5, 4.2, -0.35],
    [1.5, -4.6, -0.35],
    [17.6, -6.1, 1.35],
    [17.6, -3.4, 1.35],
  ];
  mesh.slab(wing, 2, 0.62, WHITE, SHADE);
  mesh.slab(mirrored(wing), 2, 0.62, WHITE, SHADE);

  const winglet: Vec3[] = [
    [17.75, -3.5, 1.6],
    [17.75, -4.4, 4.4],
    [17.75, -5.6, 4.4],
    [17.75, -6.0, 1.6],
  ];
  mesh.slab(winglet, 0, 0.3, GOLD, GOLD);
  mesh.slab(mirrored(winglet), 0, 0.3, GOLD, GOLD);

  const stab: Vec3[] = [
    [0.9, -10.6, 1.15],
    [0.9, -14.2, 1.15],
    [7.4, -14.9, 1.65],
    [7.4, -13.3, 1.65],
  ];
  mesh.slab(stab, 2, 0.34, WHITE, SHADE);
  mesh.slab(mirrored(stab), 2, 0.34, WHITE, SHADE);

  const fin: Vec3[] = [
    [0, -9.0, 1.2],
    [0, -12.2, 7.2],
    [0, -15.2, 7.2],
    [0, -14.4, 1.2],
  ];
  mesh.slab(fin, 0, 0.44, GOLD, GOLD);

  tube(mesh, 8.6, -2.5, -1.6, 4.6, 1.65);
  tube(mesh, -8.6, -2.5, -1.6, 4.6, 1.65);

  return {
    positions: new Float32Array(mesh.positions),
    normals: new Float32Array(mesh.normals),
    colors: new Float32Array(mesh.colors),
    count: mesh.positions.length / 3,
  };
}

const EARTH_RADIUS = 6371008.8;

function mercatorAnchor(
  lon: number,
  lat: number,
  altitude: number
): { x: number; y: number; z: number; meter: number } {
  const clamped = Math.max(-85.051129, Math.min(85.051129, lat));
  const x = (180 + lon) / 360;
  const y =
    (180 -
      (180 / Math.PI) *
        Math.log(Math.tan(Math.PI / 4 + (clamped * Math.PI) / 360))) /
    360;
  const circumference = 2 * Math.PI * EARTH_RADIUS * Math.cos(clamped * (Math.PI / 180));
  const meter = 1 / circumference;
  return { x, y, z: altitude * meter, meter };
}

function identity(): Float64Array {
  const out = new Float64Array(16);
  out[0] = 1;
  out[5] = 1;
  out[10] = 1;
  out[15] = 1;
  return out;
}

function multiply(a: Float64Array, b: Float64Array): Float64Array {
  const out = new Float64Array(16);
  for (let column = 0; column < 4; column += 1) {
    for (let row = 0; row < 4; row += 1) {
      out[column * 4 + row] =
        a[row] * b[column * 4] +
        a[4 + row] * b[column * 4 + 1] +
        a[8 + row] * b[column * 4 + 2] +
        a[12 + row] * b[column * 4 + 3];
    }
  }
  return out;
}

function translation(x: number, y: number, z: number): Float64Array {
  const out = identity();
  out[12] = x;
  out[13] = y;
  out[14] = z;
  return out;
}

function scaling(x: number, y: number, z: number): Float64Array {
  const out = identity();
  out[0] = x;
  out[5] = y;
  out[10] = z;
  return out;
}

function rotationX(angle: number): Float64Array {
  const out = identity();
  const sin = Math.sin(angle);
  const cos = Math.cos(angle);
  out[5] = cos;
  out[6] = sin;
  out[9] = -sin;
  out[10] = cos;
  return out;
}

function rotationY(angle: number): Float64Array {
  const out = identity();
  const sin = Math.sin(angle);
  const cos = Math.cos(angle);
  out[0] = cos;
  out[2] = -sin;
  out[8] = sin;
  out[10] = cos;
  return out;
}

function rotationZ(angle: number): Float64Array {
  const out = identity();
  const sin = Math.sin(angle);
  const cos = Math.cos(angle);
  out[0] = cos;
  out[1] = sin;
  out[4] = -sin;
  out[5] = cos;
  return out;
}

const VERTEX_SOURCE = `
attribute vec3 a_pos;
attribute vec3 a_normal;
attribute vec3 a_color;
uniform mat4 u_matrix;
uniform mat4 u_rotation;
varying vec3 v_normal;
varying vec3 v_color;
void main() {
  v_normal = (u_rotation * vec4(a_normal, 0.0)).xyz;
  v_color = a_color;
  gl_Position = u_matrix * vec4(a_pos, 1.0);
}
`;

const FRAGMENT_SOURCE = `
precision mediump float;
uniform vec3 u_light;
uniform float u_opacity;
varying vec3 v_normal;
varying vec3 v_color;
void main() {
  vec3 normal = normalize(v_normal);
  float lambert = abs(dot(normal, u_light));
  float sky = 0.5 + 0.5 * normal.z;
  vec3 shaded = v_color * (0.34 + 0.72 * lambert);
  shaded += vec3(0.09, 0.11, 0.16) * sky;
  float rim = pow(1.0 - abs(normal.z), 4.0) * 0.12;
  gl_FragColor = vec4(shaded + rim, u_opacity);
}
`;

function compile(
  gl: WebGLRenderingContext | WebGL2RenderingContext,
  type: number,
  source: string
): WebGLShader | null {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  return shader;
}

export function planeMatrix(pose: PlanePose): {
  model: Float64Array;
  rotation: Float64Array;
} {
  const anchor = mercatorAnchor(pose.lon, pose.lat, pose.altitude);
  const meters = anchor.meter * pose.scale;
  const rotation = multiply(
    multiply(
      rotationZ(-(pose.heading * Math.PI) / 180),
      rotationX((pose.pitch * Math.PI) / 180)
    ),
    rotationY((pose.roll * Math.PI) / 180)
  );
  const model = multiply(
    multiply(
      translation(anchor.x, anchor.y, anchor.z),
      scaling(meters, -meters, meters)
    ),
    rotation
  );
  return { model, rotation };
}

export class PlaneLayer implements maplibregl.CustomLayerInterface {
  id = "jon-flugzeug";
  type = "custom" as const;
  renderingMode = "3d" as const;

  private pose: PlanePose = {
    lon: 0,
    lat: 0,
    altitude: 0,
    heading: 0,
    pitch: 0,
    roll: 0,
    visible: false,
    scale: 1,
  };
  private program: WebGLProgram | null = null;
  private buffers: {
    position: WebGLBuffer | null;
    normal: WebGLBuffer | null;
    color: WebGLBuffer | null;
  } = { position: null, normal: null, color: null };
  private locations: Record<string, number> = {};
  private uniforms: Record<string, WebGLUniformLocation | null> = {};
  private count = 0;

  set(pose: PlanePose): void {
    this.pose = pose;
  }

  onAdd(_map: maplibregl.Map, gl: WebGLRenderingContext | WebGL2RenderingContext): void {
    const vertex = compile(gl, gl.VERTEX_SHADER, VERTEX_SOURCE);
    const fragment = compile(gl, gl.FRAGMENT_SHADER, FRAGMENT_SOURCE);
    const program = gl.createProgram();
    if (!vertex || !fragment || !program) return;
    gl.attachShader(program, vertex);
    gl.attachShader(program, fragment);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      gl.deleteProgram(program);
      return;
    }
    this.program = program;
    this.locations = {
      position: gl.getAttribLocation(program, "a_pos"),
      normal: gl.getAttribLocation(program, "a_normal"),
      color: gl.getAttribLocation(program, "a_color"),
    };
    this.uniforms = {
      matrix: gl.getUniformLocation(program, "u_matrix"),
      rotation: gl.getUniformLocation(program, "u_rotation"),
      light: gl.getUniformLocation(program, "u_light"),
      opacity: gl.getUniformLocation(program, "u_opacity"),
    };
    const model = buildPlane();
    this.count = model.count;
    const upload = (data: Float32Array): WebGLBuffer | null => {
      const buffer = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
      return buffer;
    };
    this.buffers = {
      position: upload(model.positions),
      normal: upload(model.normals),
      color: upload(model.colors),
    };
  }

  onRemove(_map: maplibregl.Map, gl: WebGLRenderingContext | WebGL2RenderingContext): void {
    Object.values(this.buffers).forEach((buffer) => {
      if (buffer) gl.deleteBuffer(buffer);
    });
    if (this.program) gl.deleteProgram(this.program);
    this.program = null;
  }

  render(
    gl: WebGLRenderingContext | WebGL2RenderingContext,
    options: maplibregl.CustomRenderMethodInput
  ): void {
    const pose = this.pose;
    if (!this.program || !pose.visible || this.count === 0) return;
    const { model, rotation } = planeMatrix(pose);
    const view = new Float64Array(options.modelViewProjectionMatrix as ArrayLike<number>);
    const matrix = multiply(view, model);

    gl.useProgram(this.program);
    gl.uniformMatrix4fv(
      this.uniforms.matrix,
      false,
      new Float32Array(matrix)
    );
    gl.uniformMatrix4fv(
      this.uniforms.rotation,
      false,
      new Float32Array(rotation)
    );
    gl.uniform3f(this.uniforms.light, 0.36, 0.42, 0.83);
    gl.uniform1f(this.uniforms.opacity, 1);

    const bind = (buffer: WebGLBuffer | null, location: number) => {
      if (!buffer || location < 0) return;
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.enableVertexAttribArray(location);
      gl.vertexAttribPointer(location, 3, gl.FLOAT, false, 0, 0);
    };
    bind(this.buffers.position, this.locations.position);
    bind(this.buffers.normal, this.locations.normal);
    bind(this.buffers.color, this.locations.color);

    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    gl.disable(gl.CULL_FACE);
    gl.disable(gl.BLEND);
    gl.drawArrays(gl.TRIANGLES, 0, this.count);
    gl.enable(gl.BLEND);
  }
}
