(function () {
  const VS = [
    "attribute vec3 aPos;",
    "attribute vec3 aNormal;",
    "uniform mat4 uProj;",
    "uniform mat4 uView;",
    "uniform mat4 uModel;",
    "uniform mat3 uNormal;",
    "varying vec3 vNormal;",
    "varying vec3 vWorld;",
    "void main() {",
    "  vec4 world = uModel * vec4(aPos, 1.0);",
    "  vWorld = world.xyz;",
    "  vNormal = normalize(uNormal * aNormal);",
    "  gl_Position = uProj * uView * world;",
    "}",
  ].join("\n");

  const FS = [
    "precision mediump float;",
    "varying vec3 vNormal;",
    "varying vec3 vWorld;",
    "uniform vec3 uColor;",
    "uniform vec3 uLight;",
    "uniform vec3 uEye;",
    "uniform float uShine;",
    "uniform float uAmbient;",
    "uniform float uFur;",
    "void main() {",
    "  vec3 n = normalize(vNormal);",
    "  vec3 v = normalize(uEye - vWorld);",
    "  vec3 key = normalize(uLight);",
    "  vec3 fill = normalize(vec3(0.85, 0.15, 0.5));",
    "  vec3 back = normalize(vec3(-0.3, 0.4, -1.0));",
    "  float wrap = mix(0.22, 0.62, uFur);",
    "  float dKey = max((dot(n, key) + wrap) / (1.0 + wrap), 0.0);",
    "  float dFill = max((dot(n, fill) + 0.55) / 1.55, 0.0);",
    "  float dBack = max(dot(n, back), 0.0);",
    "  float sky = n.y * 0.5 + 0.5;",
    "  vec3 ambient = mix(vec3(0.30, 0.31, 0.38), vec3(0.92, 0.94, 1.0), sky) * uAmbient;",
    "  vec3 light = ambient + vec3(1.0, 0.95, 0.88) * dKey * 0.92 +",
    "               vec3(0.55, 0.64, 0.92) * dFill * 0.3 +",
    "               vec3(0.9, 0.84, 0.78) * dBack * 0.16;",
    "  vec3 base = uColor * light;",
    "  vec3 h = normalize(key + v);",
    "  float rough = mix(96.0, 14.0, uFur);",
    "  float spec = pow(max(dot(n, h), 0.0), rough) * uShine * (1.0 - uFur * 0.6);",
    "  float facing = 1.0 - max(dot(n, v), 0.0);",
    "  float fluff = pow(facing, 2.1) * uFur * (0.2 + dKey * 0.7);",
    "  float fresnel = pow(facing, 4.5) * (1.0 - uFur) * 0.5;",
    "  vec3 color = base + vec3(1.0, 0.97, 0.92) * spec + uColor * fluff * 0.9 +",
    "               vec3(0.6, 0.68, 0.9) * fresnel;",
    "  vec3 x = color * 1.04;",
    "  vec3 mapped = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14);",
    "  gl_FragColor = vec4(pow(clamp(mapped, 0.0, 1.0), vec3(0.95)), 1.0);",
    "}",
  ].join("\n");

  function compile(gl, type, src) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, src);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      gl.deleteShader(shader);
      return null;
    }
    return shader;
  }

  function buildProgram(gl) {
    const vs = compile(gl, gl.VERTEX_SHADER, VS);
    const fs = compile(gl, gl.FRAGMENT_SHADER, FS);
    if (!vs || !fs) return null;
    const prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return null;
    return prog;
  }

  function sphereData(segments, rings) {
    const pos = [];
    const nor = [];
    const idx = [];
    for (let y = 0; y <= rings; y++) {
      const phi = (y / rings) * Math.PI;
      for (let x = 0; x <= segments; x++) {
        const theta = (x / segments) * Math.PI * 2;
        const nx = Math.sin(phi) * Math.cos(theta);
        const ny = Math.cos(phi);
        const nz = Math.sin(phi) * Math.sin(theta);
        pos.push(nx, ny, nz);
        nor.push(nx, ny, nz);
      }
    }
    for (let y = 0; y < rings; y++) {
      for (let x = 0; x < segments; x++) {
        const a = y * (segments + 1) + x;
        const b = a + segments + 1;
        idx.push(a, b, a + 1, b, b + 1, a + 1);
      }
    }
    return { pos, nor, idx };
  }

  function coneData(segments) {
    const pos = [0, 1, 0];
    const nor = [0, 1, 0];
    const idx = [];
    for (let i = 0; i <= segments; i++) {
      const t = (i / segments) * Math.PI * 2;
      const x = Math.cos(t);
      const z = Math.sin(t);
      pos.push(x, -1, z);
      const len = Math.sqrt(x * x + 0.25 + z * z);
      nor.push(x / len, 0.5 / len, z / len);
    }
    for (let i = 1; i <= segments; i++) idx.push(0, i, i + 1);
    const center = pos.length / 3;
    pos.push(0, -1, 0);
    nor.push(0, -1, 0);
    for (let i = 1; i <= segments; i++) idx.push(center, i + 1, i);
    return { pos, nor, idx };
  }

  function torusData(segments, sides, thickness) {
    const pos = [];
    const nor = [];
    const idx = [];
    for (let i = 0; i <= segments; i++) {
      const u = (i / segments) * Math.PI * 2;
      const cu = Math.cos(u);
      const su = Math.sin(u);
      for (let j = 0; j <= sides; j++) {
        const v = (j / sides) * Math.PI * 2;
        const cv = Math.cos(v);
        const sv = Math.sin(v);
        pos.push((1 + thickness * cv) * cu, (1 + thickness * cv) * su, thickness * sv);
        nor.push(cv * cu, cv * su, sv);
      }
    }
    for (let i = 0; i < segments; i++) {
      for (let j = 0; j < sides; j++) {
        const a = i * (sides + 1) + j;
        const b = a + sides + 1;
        idx.push(a, b, a + 1, b, b + 1, a + 1);
      }
    }
    return { pos, nor, idx };
  }

  function upload(gl, data) {
    const posBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(data.pos), gl.STATIC_DRAW);
    const norBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, norBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(data.nor), gl.STATIC_DRAW);
    const idxBuf = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);
    gl.bufferData(
      gl.ELEMENT_ARRAY_BUFFER,
      new Uint16Array(data.idx),
      gl.STATIC_DRAW
    );
    return { posBuf, norBuf, idxBuf, count: data.idx.length };
  }

  function identity() {
    return [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
  }

  function multiply(a, b) {
    const out = new Array(16);
    for (let c = 0; c < 4; c++) {
      for (let r = 0; r < 4; r++) {
        out[c * 4 + r] =
          a[r] * b[c * 4] +
          a[4 + r] * b[c * 4 + 1] +
          a[8 + r] * b[c * 4 + 2] +
          a[12 + r] * b[c * 4 + 3];
      }
    }
    return out;
  }

  function translation(x, y, z) {
    const m = identity();
    m[12] = x;
    m[13] = y;
    m[14] = z;
    return m;
  }

  function scaling(x, y, z) {
    const m = identity();
    m[0] = x;
    m[5] = y;
    m[10] = z;
    return m;
  }

  function rotationX(a) {
    const c = Math.cos(a);
    const s = Math.sin(a);
    const m = identity();
    m[5] = c;
    m[6] = s;
    m[9] = -s;
    m[10] = c;
    return m;
  }

  function rotationY(a) {
    const c = Math.cos(a);
    const s = Math.sin(a);
    const m = identity();
    m[0] = c;
    m[2] = -s;
    m[8] = s;
    m[10] = c;
    return m;
  }

  function rotationZ(a) {
    const c = Math.cos(a);
    const s = Math.sin(a);
    const m = identity();
    m[0] = c;
    m[1] = s;
    m[4] = -s;
    m[5] = c;
    return m;
  }

  function perspective(fov, aspect, near, far) {
    const f = 1 / Math.tan(fov / 2);
    const m = new Array(16).fill(0);
    m[0] = f / aspect;
    m[5] = f;
    m[10] = (far + near) / (near - far);
    m[11] = -1;
    m[14] = (2 * far * near) / (near - far);
    return m;
  }

  function lookAt(eye, target, up) {
    const z = normalize([eye[0] - target[0], eye[1] - target[1], eye[2] - target[2]]);
    const x = normalize(cross(up, z));
    const y = cross(z, x);
    return [
      x[0], y[0], z[0], 0,
      x[1], y[1], z[1], 0,
      x[2], y[2], z[2], 0,
      -dot(x, eye), -dot(y, eye), -dot(z, eye), 1,
    ];
  }

  function cross(a, b) {
    return [
      a[1] * b[2] - a[2] * b[1],
      a[2] * b[0] - a[0] * b[2],
      a[0] * b[1] - a[1] * b[0],
    ];
  }

  function dot(a, b) {
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  }

  function normalize(v) {
    const len = Math.sqrt(dot(v, v)) || 1;
    return [v[0] / len, v[1] / len, v[2] / len];
  }

  function normalMatrix(m) {
    const a = m[0], b = m[1], c = m[2];
    const d = m[4], e = m[5], f = m[6];
    const g = m[8], h = m[9], i = m[10];
    const det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g);
    if (!det) return [1, 0, 0, 0, 1, 0, 0, 0, 1];
    const inv = 1 / det;
    return [
      (e * i - f * h) * inv, (c * h - b * i) * inv, (b * f - c * e) * inv,
      (f * g - d * i) * inv, (a * i - c * g) * inv, (c * d - a * f) * inv,
      (d * h - e * g) * inv, (b * g - a * h) * inv, (a * e - b * d) * inv,
    ];
  }

  function hexToRgb(hex) {
    const clean = String(hex || "").replace("#", "");
    const full =
      clean.length === 3
        ? clean.split("").map((c) => c + c).join("")
        : clean.padEnd(6, "0");
    const num = parseInt(full.slice(0, 6), 16);
    if (Number.isNaN(num)) return [0.83, 0.69, 0.22];
    return [
      ((num >> 16) & 255) / 255,
      ((num >> 8) & 255) / 255,
      (num & 255) / 255,
    ];
  }

  function mix(a, b, t) {
    return [
      a[0] + (b[0] - a[0]) * t,
      a[1] + (b[1] - a[1]) * t,
      a[2] + (b[2] - a[2]) * t,
    ];
  }

  const BLACK = [0.05, 0.05, 0.07];
  const WHITE = [0.97, 0.97, 1];
  const ROSEWHITE = [1, 0.965, 0.98];
  const PINK = [1, 0.7, 0.76];
  const CAT_BODY = [0.36, 0.36, 0.4];
  const CAT_HEAD = [0.44, 0.44, 0.49];
  const DOG_BODY = [0.73, 0.55, 0.35];
  const DOG_HEAD = [0.8, 0.63, 0.42];
  const DOG_EAR = [0.55, 0.38, 0.21];
  const DOG_SNOUT = [0.93, 0.86, 0.75];

  function create(canvas) {
    const gl =
      canvas.getContext("webgl", { alpha: true, antialias: true, premultipliedAlpha: false }) ||
      canvas.getContext("experimental-webgl", { alpha: true, antialias: true });
    if (!gl) return null;
    const prog = buildProgram(gl);
    if (!prog) return null;

    const meshes = {
      sphere: upload(gl, sphereData(34, 24)),
      cone: upload(gl, coneData(20)),
      ring: upload(gl, torusData(48, 14, 0.075)),
    };
    const loc = {
      pos: gl.getAttribLocation(prog, "aPos"),
      normal: gl.getAttribLocation(prog, "aNormal"),
      proj: gl.getUniformLocation(prog, "uProj"),
      view: gl.getUniformLocation(prog, "uView"),
      model: gl.getUniformLocation(prog, "uModel"),
      normalMat: gl.getUniformLocation(prog, "uNormal"),
      color: gl.getUniformLocation(prog, "uColor"),
      light: gl.getUniformLocation(prog, "uLight"),
      eye: gl.getUniformLocation(prog, "uEye"),
      shine: gl.getUniformLocation(prog, "uShine"),
      ambient: gl.getUniformLocation(prog, "uAmbient"),
      fur: gl.getUniformLocation(prog, "uFur"),
    };

    const eye = [0, 0.35, 5.2];
    const state = {
      kind: "jon",
      accent: [0.83, 0.69, 0.22],
      face: [0.04, 0.04, 0.055],
      light: false,
      cozy: false,
      mouth: 0,
      eyes: 1,
      sleep: false,
      facing: 1,
      spin: 0,
      time: 0,
      running: false,
      frame: 0,
      last: 0,
    };

    function drawPart(mesh, model, color, shine, fur) {
      gl.bindBuffer(gl.ARRAY_BUFFER, mesh.posBuf);
      gl.enableVertexAttribArray(loc.pos);
      gl.vertexAttribPointer(loc.pos, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, mesh.norBuf);
      gl.enableVertexAttribArray(loc.normal);
      gl.vertexAttribPointer(loc.normal, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, mesh.idxBuf);
      gl.uniformMatrix4fv(loc.model, false, new Float32Array(model));
      gl.uniformMatrix3fv(loc.normalMat, false, new Float32Array(normalMatrix(model)));
      gl.uniform3fv(loc.color, new Float32Array(color));
      gl.uniform1f(loc.shine, shine === undefined ? 0.35 : shine);
      gl.uniform1f(loc.fur, fur === undefined ? 0 : fur);
      gl.drawElements(gl.TRIANGLES, mesh.count, gl.UNSIGNED_SHORT, 0);
    }

    function part(mesh, color, ops, shine, fur) {
      return { mesh, color, ops, shine, fur };
    }

    function place(ops) {
      let m = identity();
      for (const op of ops) m = multiply(m, op);
      return m;
    }

    function jonParts() {
      const lid = state.sleep ? 0 : state.eyes;
      const open = state.mouth;
      const parts = [
        part(meshes.sphere, state.face, [scaling(1, 1, 1)], 0.7, 0),
        part(
          meshes.ring,
          state.accent,
          [translation(0, 0, 0.02), scaling(1.008, 1.008, 1.008)],
          0.95,
          0
        ),
      ];
      const eyeY = 0.17;
      const eyeX = 0.33;
      const offen = Math.max(lid, 0.07);
      const eyeZ = Math.sqrt(Math.max(1 - eyeX * eyeX - eyeY * eyeY, 0.04)) - 0.06;
      for (const sx of [-1, 1]) {
        parts.push(
          part(
            meshes.sphere,
            mix(state.accent, BLACK, 0.55),
            [translation(sx * eyeX, eyeY, eyeZ), scaling(0.165, 0.165 * offen, 0.1)],
            0.35,
            0
          )
        );
        parts.push(
          part(
            meshes.sphere,
            state.accent,
            [translation(sx * eyeX, eyeY, eyeZ + 0.035), scaling(0.13, 0.13 * offen, 0.09)],
            0.9,
            0
          )
        );
        parts.push(
          part(
            meshes.sphere,
            WHITE,
            [
              translation(sx * eyeX - 0.048, eyeY + 0.052, eyeZ + 0.075),
              scaling(0.038, 0.038 * Math.max(offen, 0.35), 0.03),
            ],
            1,
            0
          )
        );
      }
      if (open > 0.02) {
        parts.push(
          part(
            meshes.sphere,
            mix(state.accent, BLACK, 0.4),
            [translation(0, -0.3, 0.83), scaling(0.26, 0.08 + open * 0.26, 0.11)],
            0.6,
            0
          )
        );
      } else {
        const perlen = 9;
        for (let i = 0; i < perlen; i++) {
          const t = i / (perlen - 1);
          const x = (t - 0.5) * 0.66;
          const y = -0.2 - Math.sin(t * Math.PI) * 0.16;
          const z = Math.sqrt(Math.max(1 - x * x - y * y, 0.04)) + 0.012;
          const r = 0.062 - Math.abs(t - 0.5) * 0.022;
          parts.push(
            part(meshes.sphere, state.accent, [translation(x, y, z), scaling(r, r, r * 0.7)], 0.9, 0)
          );
        }
      }
      return parts;
    }

    function augenPaar(parts, sx, y, z, lid, iris, weite) {
      const offen = Math.max(lid, 0.08);
      parts.push(
        part(
          meshes.sphere,
          [0.93, 0.92, 0.94],
          [translation(sx * weite, y, z - 0.02), scaling(0.115, 0.115 * offen, 0.09)],
          0.5,
          0
        )
      );
      parts.push(
        part(
          meshes.sphere,
          iris,
          [translation(sx * weite, y, z + 0.03), scaling(0.088, 0.09 * offen, 0.06)],
          0.85,
          0
        )
      );
      parts.push(
        part(
          meshes.sphere,
          [0.04, 0.03, 0.05],
          [translation(sx * weite, y, z + 0.05), scaling(0.042, 0.072 * offen, 0.04)],
          0.95,
          0
        )
      );
      parts.push(
        part(
          meshes.sphere,
          WHITE,
          [
            translation(sx * weite - 0.032, y + 0.038, z + 0.07),
            scaling(0.026, 0.026 * Math.max(offen, 0.4), 0.02),
          ],
          1,
          0
        )
      );
    }

    function beine(parts, farbe, pfote, vornY, hintenY, z, spreiz) {
      for (const sx of [-1, 1]) {
        parts.push(
          part(
            meshes.sphere,
            farbe,
            [translation(sx * spreiz, vornY, z), scaling(0.15, 0.26, 0.17)],
            0.15
          )
        );
        parts.push(
          part(
            meshes.sphere,
            pfote,
            [translation(sx * spreiz, vornY - 0.22, z + 0.06), scaling(0.16, 0.1, 0.2)],
            0.2
          )
        );
        parts.push(
          part(
            meshes.sphere,
            farbe,
            [translation(sx * (spreiz + 0.22), hintenY, -z * 0.72), scaling(0.24, 0.26, 0.28)],
            0.15
          )
        );
      }
    }

    function schweif(parts, farbe, wurzel, laenge, kruemmung, dicke, wedeln) {
      const glieder = 6;
      for (let i = 0; i < glieder; i++) {
        const t = i / (glieder - 1);
        const winkel = kruemmung * t + wedeln * t;
        const x = wurzel[0] + Math.cos(winkel) * laenge * t;
        const y = wurzel[1] + Math.sin(winkel) * laenge * t;
        const z = wurzel[2] - t * 0.12;
        const r = dicke * (1 - t * 0.42);
        parts.push(part(meshes.sphere, farbe, [translation(x, y, z), scaling(r, r, r)], 0.15));
      }
    }

    function catParts() {
      const lid = state.sleep ? 0.05 : state.eyes;
      const body = CAT_BODY;
      const head = CAT_HEAD;
      const bauch = mix(body, WHITE, 0.55);
      const parts = [
        part(meshes.sphere, body, [translation(0, -0.58, -0.02), scaling(0.82, 0.62, 0.72)], 0.2),
        part(meshes.sphere, bauch, [translation(0, -0.66, 0.34), scaling(0.5, 0.42, 0.4)], 0.2),
        part(meshes.sphere, body, [translation(0, -0.18, 0.02), scaling(0.5, 0.34, 0.46)], 0.2),
      ];
      beine(parts, body, bauch, -1.0, -0.78, 0.52, 0.4);
      schweif(
        parts,
        body,
        [0.78, -0.62, -0.44],
        1.05,
        0.55,
        0.13,
        Math.sin(state.time * 1.6) * 0.45
      );
      parts.push(
        part(meshes.sphere, head, [translation(0, 0.38, 0.12), scaling(0.62, 0.56, 0.58)], 0.25)
      );
      parts.push(
        part(meshes.sphere, head, [translation(0, 0.2, 0.46), scaling(0.34, 0.24, 0.26)], 0.25)
      );
      for (const sx of [-1, 1]) {
        parts.push(
          part(
            meshes.cone,
            head,
            [translation(sx * 0.38, 0.84, 0.02), rotationZ(sx * -0.28), scaling(0.21, 0.3, 0.17)],
            0.2
          )
        );
        parts.push(
          part(
            meshes.cone,
            PINK,
            [translation(sx * 0.37, 0.82, 0.09), rotationZ(sx * -0.28), scaling(0.11, 0.19, 0.1)],
            0.2,
            0.3
          )
        );
        parts.push(
          part(
            meshes.sphere,
            mix(head, WHITE, 0.3),
            [translation(sx * 0.42, 0.28, 0.28), scaling(0.19, 0.16, 0.14)],
            0.2
          )
        );
        parts.push(
          part(
            meshes.sphere,
            [0.2, 0.2, 0.24],
            [translation(sx * 0.52, 0.24, 0.36), rotationZ(sx * 0.22), scaling(0.26, 0.011, 0.011)],
            0.1,
            0
          )
        );
        parts.push(
          part(
            meshes.sphere,
            [0.2, 0.2, 0.24],
            [translation(sx * 0.5, 0.18, 0.36), rotationZ(sx * 0.05), scaling(0.24, 0.011, 0.011)],
            0.1,
            0
          )
        );
        augenPaar(parts, sx, 0.44, 0.62, lid, [0.62, 0.78, 0.4], 0.23);
      }
      parts.push(
        part(meshes.sphere, WHITE, [translation(0, 0.2, 0.52), scaling(0.24, 0.15, 0.2)], 0.3)
      );
      parts.push(
        part(meshes.sphere, PINK, [translation(0, 0.27, 0.66), scaling(0.065, 0.048, 0.055)], 0.85, 0.2)
      );
      return parts;
    }

    function dogParts() {
      const lid = state.sleep ? 0.05 : state.eyes;
      const bauch = mix(DOG_BODY, WHITE, 0.5);
      const parts = [
        part(meshes.sphere, DOG_BODY, [translation(0, -0.58, -0.02), scaling(0.86, 0.62, 0.74)], 0.2),
        part(meshes.sphere, bauch, [translation(0, -0.62, 0.36), scaling(0.5, 0.44, 0.4)], 0.2),
        part(meshes.sphere, DOG_BODY, [translation(0, -0.16, 0.0), scaling(0.52, 0.36, 0.48)], 0.2),
      ];
      beine(parts, DOG_BODY, bauch, -1.0, -0.76, 0.54, 0.42);
      schweif(
        parts,
        DOG_BODY,
        [0.76, -0.46, -0.46],
        0.78,
        1.05,
        0.14,
        Math.sin(state.time * 4.2) * 0.5
      );
      parts.push(
        part(meshes.sphere, DOG_HEAD, [translation(0, 0.38, 0.12), scaling(0.62, 0.58, 0.58)], 0.25)
      );
      parts.push(
        part(meshes.sphere, DOG_SNOUT, [translation(0, 0.19, 0.52), scaling(0.31, 0.23, 0.3)], 0.3)
      );
      parts.push(
        part(
          meshes.sphere,
          [0.14, 0.1, 0.08],
          [translation(0, 0.27, 0.78), scaling(0.105, 0.082, 0.07)],
          1,
          0
        )
      );
      parts.push(
        part(
          meshes.sphere,
          [0.28, 0.19, 0.16],
          [translation(0, 0.11, 0.72), scaling(0.14, 0.035, 0.09)],
          0.4,
          0
        )
      );
      for (const sx of [-1, 1]) {
        parts.push(
          part(
            meshes.sphere,
            DOG_EAR,
            [translation(sx * 0.56, 0.42, 0.0), rotationZ(sx * -0.2), scaling(0.17, 0.38, 0.15)],
            0.2
          )
        );
        parts.push(
          part(
            meshes.sphere,
            mix(DOG_EAR, PINK, 0.35),
            [translation(sx * 0.5, 0.42, 0.08), rotationZ(sx * -0.2), scaling(0.09, 0.26, 0.08)],
            0.2,
            0.4
          )
        );
        parts.push(
          part(
            meshes.sphere,
            mix(DOG_HEAD, WHITE, 0.25),
            [translation(sx * 0.2, 0.62, 0.42), scaling(0.13, 0.05, 0.07)],
            0.2
          )
        );
        augenPaar(parts, sx, 0.48, 0.6, lid, [0.42, 0.26, 0.14], 0.22);
      }
      return parts;
    }

    function scene() {
      if (state.kind === "cat") return catParts();
      if (state.kind === "dog") return dogParts();
      return jonParts();
    }

    function render() {
      const width = canvas.clientWidth || canvas.width;
      const height = canvas.clientHeight || canvas.height;
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      const w = Math.max(1, Math.round(width * ratio));
      const h = Math.max(1, Math.round(height * ratio));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.enable(gl.DEPTH_TEST);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.useProgram(prog);

      const aspect = canvas.width / canvas.height;
      const proj = perspective(0.62, aspect, 0.1, 40);
      const view = lookAt(eye, [0, state.kind === "jon" ? 0 : -0.1, 0], [0, 1, 0]);
      gl.uniformMatrix4fv(loc.proj, false, new Float32Array(proj));
      gl.uniformMatrix4fv(loc.view, false, new Float32Array(view));
      gl.uniform3fv(loc.light, new Float32Array([-0.55, 0.75, 0.9]));
      gl.uniform3fv(loc.eye, new Float32Array(eye));
      gl.uniform1f(loc.ambient, state.cozy ? 0.6 : state.light ? 0.52 : 0.32);

      const sway = Math.sin(state.time * 0.7) * 0.34;
      const nod = Math.sin(state.time * 0.9) * 0.06;
      const bob = Math.sin(state.time * 1.15) * 0.045;
      const scale = state.kind === "jon" ? 1.42 : 1.25;
      const root = place([
        translation(0, bob, 0),
        rotationY(sway + (state.facing < 0 ? Math.PI * 0.32 : 0)),
        rotationX(nod),
        scaling(scale * state.facing, scale, scale),
      ]);

      const pelzig = state.kind === "cat" || state.kind === "dog";
      for (const item of scene()) {
        const fur = item.fur === undefined ? (pelzig ? 0.85 : 0) : item.fur;
        drawPart(item.mesh, multiply(root, place(item.ops)), item.color, item.shine, fur);
      }
    }

    function loop(now) {
      if (!state.running) return;
      const delta = state.last ? Math.min((now - state.last) / 1000, 0.1) : 0.016;
      state.last = now;
      state.time += delta;
      render();
      state.frame = window.requestAnimationFrame(loop);
    }

    const api = {
      setKind(kind) {
        state.kind = kind === "cat" || kind === "dog" ? kind : "jon";
      },
      setColors(colors) {
        if (colors.accent) state.accent = hexToRgb(colors.accent);
        if (colors.face) state.face = hexToRgb(colors.face);
        state.cozy = colors.cozy === true;
        state.light = colors.light === true || state.cozy;
        if (state.cozy) state.face = mix(state.face, ROSEWHITE, 0.95);
        else if (state.light) state.face = mix(state.face, WHITE, 0.92);
      },
      setMouth(value) {
        state.mouth = Math.max(0, Math.min(1, value));
      },
      setEyes(value) {
        state.eyes = Math.max(0, Math.min(1, value));
      },
      setSleep(value) {
        state.sleep = value === true;
      },
      setFacing(value) {
        state.facing = value < 0 ? -1 : 1;
      },
      start() {
        if (state.running) return;
        state.running = true;
        state.last = 0;
        state.frame = window.requestAnimationFrame(loop);
      },
      stop() {
        state.running = false;
        if (state.frame) window.cancelAnimationFrame(state.frame);
        state.frame = 0;
      },
      render,
      destroy() {
        api.stop();
        const ext = gl.getExtension("WEBGL_lose_context");
        if (ext) ext.loseContext();
      },
    };
    return api;
  }

  window.Jon3D = { create };
})();
