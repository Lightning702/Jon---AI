#version 330 core

in vec2 vUV;
out vec4 oColor;

uniform sampler2D uSource;
uniform vec2 uTexelSize;
uniform float uRadius;

void main() {
    vec2 t = uTexelSize * uRadius;

    vec3 a = texture(uSource, vUV + vec2(-t.x, t.y)).rgb;
    vec3 b = texture(uSource, vUV + vec2(0.0, t.y)).rgb;
    vec3 c = texture(uSource, vUV + vec2(t.x, t.y)).rgb;
    vec3 d = texture(uSource, vUV + vec2(-t.x, 0.0)).rgb;
    vec3 e = texture(uSource, vUV).rgb;
    vec3 f = texture(uSource, vUV + vec2(t.x, 0.0)).rgb;
    vec3 g = texture(uSource, vUV + vec2(-t.x, -t.y)).rgb;
    vec3 h = texture(uSource, vUV + vec2(0.0, -t.y)).rgb;
    vec3 i = texture(uSource, vUV + vec2(t.x, -t.y)).rgb;

    vec3 tent = e * 4.0 + (b + d + f + h) * 2.0 + (a + c + g + i);
    tent *= 1.0 / 16.0;

    oColor = vec4(tent, 1.0);
}
