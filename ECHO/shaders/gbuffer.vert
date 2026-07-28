#version 330 core

layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec4 aTangent;
layout(location = 3) in vec2 aUV;
layout(location = 4) in vec4 aColor;

uniform mat4 uModel;
uniform mat4 uViewProj;
uniform mat3 uNormalMat;
uniform vec4 uWarp;

out vec3 vWorldPos;
out vec3 vNormal;
out vec4 vTangent;
out vec2 vUV;
out vec4 vColor;

void main() {
    vec4 world = uModel * vec4(aPos, 1.0);

    if (uWarp.w > 0.001) {
        float d = length(world.xz - uWarp.xy);
        float infl = exp(-d * d * uWarp.z);
        world.y += sin(d * 1.7 - uWarp.w * 2.3) * infl * uWarp.w * 0.06;
    }

    vWorldPos = world.xyz;
    vNormal = normalize(uNormalMat * aNormal);
    vTangent = vec4(normalize(uNormalMat * aTangent.xyz), aTangent.w);
    vUV = aUV;
    vColor = aColor;
    gl_Position = uViewProj * world;
}
