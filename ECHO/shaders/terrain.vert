#version 330 core

layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec4 aTangent;
layout(location = 3) in vec2 aUV;
layout(location = 4) in vec4 aColor;

uniform mat4 uViewProj;

out vec3 vWorldPos;
out vec3 vNormal;
out vec2 vUV;
out float vBiome;
out float vHeight;
out float vSlope;

void main() {
    vWorldPos = aPos;
    vNormal = normalize(aNormal);
    vUV = aUV;
    vBiome = aColor.r * 255.0;
    vHeight = aColor.g;
    vSlope = aColor.b;
    gl_Position = uViewProj * vec4(aPos, 1.0);
}
