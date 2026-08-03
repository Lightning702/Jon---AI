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
    "void main() {",
    "  vec3 n = normalize(vNormal);",
    "  vec3 l = normalize(uLight);",
    "  vec3 v = normalize(uEye - vWorld);",
    "  vec3 h = normalize(l + v);",
    "  float diff = max(dot(n, l), 0.0);",
    "  float spec = pow(max(dot(n, h), 0.0), 42.0) * uShine;",
    "  float rim = pow(1.0 - max(dot(n, v), 0.0), 3.0) * 0.35;",
    "  vec3 base = uColor * (uAmbient + diff * 0.85);",
    "  vec3 color = base + vec3(spec) + uColor * rim;",
    "  gl_FragColor = vec4(color, 1.0);",
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
    for (let r = 0; r < 4; r++) {
      for (let c = 0; c < 4; c++) {
        out[r * 4 + c] =
          a[r * 4] * b[c] +
          a[r * 4 + 1] * b[c + 4] +
          a[r * 4 + 2] * b[c + 8] +
          a[r * 4 + 3] * b[c + 12];
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
    };

    const eye = [0, 0.35, 5.2];
    const state = {
      kind: "jon",
      accent: [0.83, 0.69, 0.22],
      face: [0.04, 0.04, 0.055],
      light: false,
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

    function drawPart(mesh, model, color, shine) {
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
      gl.drawElements(gl.TRIANGLES, mesh.count, gl.UNSIGNED_SHORT, 0);
    }

    function part(mesh, color, ops, shine) {
      return { mesh, color, ops, shine };
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
        part(meshes.sphere, state.face, [scaling(1, 1, 1)], 0.22),
        part(
          meshes.ring,
          state.accent,
          [translation(0, 0, 0.02), scaling(1.005, 1.005, 1.005)],
          0.75
        ),
      ];
      const eyeY = 0.16;
      const eyeX = 0.34;
      for (const sx of [-1, 1]) {
        parts.push(
          part(
            meshes.sphere,
            state.accent,
            [
              translation(sx * eyeX, eyeY, 0.83),
              scaling(0.14, 0.14 * Math.max(lid, 0.08), 0.1),
            ],
            0.8
          )
        );
      }
      if (open > 0.02) {
        parts.push(
          part(
            meshes.sphere,
            state.accent,
            [translation(0, -0.34, 0.8), scaling(0.24, 0.06 + open * 0.24, 0.1)],
            0.6
          )
        );
      } else {
        parts.push(
          part(
            meshes.ring,
            state.accent,
            [
              translation(0, 0.12, 0.78),
              rotationX(Math.PI / 2.35),
              scaling(0.3, 0.3, 0.3),
            ],
            0.6
          )
        );
      }
      return parts;
    }

    function catParts() {
      const lid = state.sleep ? 0.05 : state.eyes;
      const body = CAT_BODY;
      const head = CAT_HEAD;
      const parts = [
        part(meshes.sphere, body, [translation(0, -0.55, 0), scaling(0.85, 0.6, 0.7)], 0.2),
        part(
          meshes.sphere,
          body,
          [translation(0.85, -0.35, -0.15), rotationZ(-0.6), scaling(0.5, 0.12, 0.12)],
          0.2
        ),
        part(meshes.sphere, head, [translation(0, 0.35, 0.1), scaling(0.62, 0.58, 0.58)], 0.25),
      ];
      for (const sx of [-1, 1]) {
        parts.push(
          part(
            meshes.cone,
            head,
            [translation(sx * 0.38, 0.86, 0.02), rotationZ(sx * -0.28), scaling(0.2, 0.28, 0.16)],
            0.2
          )
        );
        parts.push(
          part(
            meshes.cone,
            PINK,
            [translation(sx * 0.38, 0.84, 0.09), rotationZ(sx * -0.28), scaling(0.11, 0.18, 0.1)],
            0.2
          )
        );
        parts.push(
          part(
            meshes.sphere,
            BLACK,
            [translation(sx * 0.22, 0.42, 0.58), scaling(0.1, 0.1 * Math.max(lid, 0.1), 0.07)],
            0.9
          )
        );
        parts.push(
          part(
            meshes.sphere,
            [0.2, 0.2, 0.24],
            [translation(sx * 0.5, 0.24, 0.35), rotationZ(sx * 0.2), scaling(0.24, 0.012, 0.012)],
            0.1
          )
        );
      }
      parts.push(
        part(meshes.sphere, WHITE, [translation(0, 0.2, 0.5), scaling(0.24, 0.16, 0.2)], 0.3)
      );
      parts.push(
        part(meshes.sphere, PINK, [translation(0, 0.26, 0.65), scaling(0.07, 0.05, 0.06)], 0.8)
      );
      return parts;
    }

    function dogParts() {
      const lid = state.sleep ? 0.05 : state.eyes;
      const parts = [
        part(meshes.sphere, DOG_BODY, [translation(0, -0.55, 0), scaling(0.9, 0.62, 0.72)], 0.2),
        part(
          meshes.sphere,
          DOG_BODY,
          [translation(0.85, -0.25, -0.2), rotationZ(-0.9), scaling(0.42, 0.13, 0.13)],
          0.2
        ),
        part(meshes.sphere, DOG_HEAD, [translation(0, 0.36, 0.1), scaling(0.63, 0.58, 0.58)], 0.25),
        part(meshes.sphere, DOG_SNOUT, [translation(0, 0.18, 0.52), scaling(0.3, 0.22, 0.28)], 0.35),
        part(meshes.sphere, [0.16, 0.11, 0.08], [translation(0, 0.26, 0.76), scaling(0.1, 0.08, 0.07)], 0.95),
      ];
      for (const sx of [-1, 1]) {
        parts.push(
          part(
            meshes.sphere,
            DOG_EAR,
            [translation(sx * 0.58, 0.42, 0.02), rotationZ(sx * -0.18), scaling(0.16, 0.36, 0.14)],
            0.2
          )
        );
        parts.push(
          part(
            meshes.sphere,
            BLACK,
            [translation(sx * 0.22, 0.48, 0.53), scaling(0.1, 0.1 * Math.max(lid, 0.1), 0.07)],
            0.9
          )
        );
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
      gl.uniform1f(loc.ambient, state.light ? 0.52 : 0.32);

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

      for (const item of scene()) {
        drawPart(item.mesh, multiply(root, place(item.ops)), item.color, item.shine);
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
        state.light = colors.light === true;
        if (state.light) state.face = mix(state.face, WHITE, 0.92);
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
