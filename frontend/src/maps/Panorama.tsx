import { useEffect, useRef } from "react";

interface Props {
  url: string;
  spherical: boolean;
  yaw: number;
  pitch: number;
  fov: number;
  onLook?: (yaw: number, pitch: number) => void;
}

const VERTEX = `
attribute vec3 aPos;
attribute vec2 aUv;
uniform mat4 uProj;
uniform mat4 uView;
varying vec2 vUv;
void main() {
  vUv = aUv;
  gl_Position = uProj * uView * vec4(aPos, 1.0);
}
`;

const FRAGMENT = `
precision mediump float;
uniform sampler2D uTex;
varying vec2 vUv;
void main() {
  gl_FragColor = texture2D(uTex, vUv);
}
`;

function perspective(fovDeg: number, aspect: number): Float32Array {
  const f = 1 / Math.tan((fovDeg * Math.PI) / 360);
  const near = 0.1;
  const far = 100;
  return new Float32Array([
    f / aspect, 0, 0, 0,
    0, f, 0, 0,
    0, 0, (far + near) / (near - far), -1,
    0, 0, (2 * far * near) / (near - far), 0,
  ]);
}

function view(yaw: number, pitch: number): Float32Array {
  const cy = Math.cos(yaw);
  const sy = Math.sin(yaw);
  const cp = Math.cos(pitch);
  const sp = Math.sin(pitch);
  return new Float32Array([
    cy, sy * sp, -sy * cp, 0,
    0, cp, sp, 0,
    sy, -cy * sp, cy * cp, 0,
    0, 0, 0, 1,
  ]);
}

function sphere(segments: number, rings: number) {
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];
  for (let ring = 0; ring <= rings; ring += 1) {
    const phi = (ring / rings) * Math.PI;
    for (let segment = 0; segment <= segments; segment += 1) {
      const theta = (segment / segments) * Math.PI * 2;
      positions.push(
        Math.sin(phi) * Math.cos(theta),
        Math.cos(phi),
        Math.sin(phi) * Math.sin(theta)
      );
      uvs.push(1 - segment / segments, ring / rings);
    }
  }
  for (let ring = 0; ring < rings; ring += 1) {
    for (let segment = 0; segment < segments; segment += 1) {
      const a = ring * (segments + 1) + segment;
      const b = a + segments + 1;
      indices.push(a, b, a + 1, b, b + 1, a + 1);
    }
  }
  return {
    positions: new Float32Array(positions),
    uvs: new Float32Array(uvs),
    indices: new Uint16Array(indices),
  };
}

export default function Panorama({ url, spherical, yaw, pitch, fov }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const glRef = useRef<WebGLRenderingContext | null>(null);
  const programRef = useRef<WebGLProgram | null>(null);
  const textureRef = useRef<WebGLTexture | null>(null);
  const countRef = useRef(0);
  const frameRef = useRef(0);
  const angles = useRef({ yaw, pitch, fov });
  angles.current = { yaw, pitch, fov };

  useEffect(() => {
    if (!spherical) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const gl = canvas.getContext("webgl", {
      antialias: true,
      alpha: false,
      preserveDrawingBuffer: false,
    });
    if (!gl) return;
    glRef.current = gl;

    const compile = (type: number, source: string) => {
      const shader = gl.createShader(type);
      if (!shader) return null;
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      return shader;
    };
    const program = gl.createProgram();
    const vertex = compile(gl.VERTEX_SHADER, VERTEX);
    const fragment = compile(gl.FRAGMENT_SHADER, FRAGMENT);
    if (!program || !vertex || !fragment) return;
    gl.attachShader(program, vertex);
    gl.attachShader(program, fragment);
    gl.linkProgram(program);
    gl.useProgram(program);
    programRef.current = program;

    const geometry = sphere(64, 32);
    countRef.current = geometry.indices.length;

    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, geometry.positions, gl.STATIC_DRAW);
    const posLocation = gl.getAttribLocation(program, "aPos");
    gl.enableVertexAttribArray(posLocation);
    gl.vertexAttribPointer(posLocation, 3, gl.FLOAT, false, 0, 0);

    const uvBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, uvBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, geometry.uvs, gl.STATIC_DRAW);
    const uvLocation = gl.getAttribLocation(program, "aUv");
    gl.enableVertexAttribArray(uvLocation);
    gl.vertexAttribPointer(uvLocation, 2, gl.FLOAT, false, 0, 0);

    const indexBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, geometry.indices, gl.STATIC_DRAW);

    const texture = gl.createTexture();
    textureRef.current = texture;
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texImage2D(
      gl.TEXTURE_2D,
      0,
      gl.RGBA,
      1,
      1,
      0,
      gl.RGBA,
      gl.UNSIGNED_BYTE,
      new Uint8Array([12, 12, 16, 255])
    );
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);

    const projLocation = gl.getUniformLocation(program, "uProj");
    const viewLocation = gl.getUniformLocation(program, "uView");

    const render = () => {
      const width = canvas.clientWidth || 1;
      const height = canvas.clientHeight || 1;
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      if (canvas.width !== width * ratio || canvas.height !== height * ratio) {
        canvas.width = width * ratio;
        canvas.height = height * ratio;
      }
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.clearColor(0.04, 0.04, 0.06, 1);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.uniformMatrix4fv(
        projLocation,
        false,
        perspective(angles.current.fov, width / height)
      );
      gl.uniformMatrix4fv(
        viewLocation,
        false,
        view(angles.current.yaw, angles.current.pitch)
      );
      gl.drawElements(gl.TRIANGLES, countRef.current, gl.UNSIGNED_SHORT, 0);
      frameRef.current = requestAnimationFrame(render);
    };
    frameRef.current = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(frameRef.current);
      gl.deleteProgram(program);
      gl.deleteTexture(texture);
      glRef.current = null;
      programRef.current = null;
    };
  }, [spherical]);

  useEffect(() => {
    if (!spherical) return;
    const gl = glRef.current;
    const texture = textureRef.current;
    if (!gl || !texture || !url) return;
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => {
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, 0);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    };
    image.src = url;
    return () => {
      image.onload = null;
    };
  }, [url, spherical]);

  if (!spherical) {
    const scale = Math.max(1, 78 / Math.max(24, fov));
    return (
      <div className="jm-pano">
        <img
          src={url}
          alt="Straßenansicht"
          draggable={false}
          style={{
            transform: `scale(${scale.toFixed(3)}) translate3d(${(
              -yaw * 90
            ).toFixed(1)}px, ${(pitch * 90).toFixed(1)}px, 0)`,
            transition: "transform 0.16s linear",
          }}
        />
      </div>
    );
  }

  return (
    <div className="jm-pano">
      <canvas ref={canvasRef} />
    </div>
  );
}
