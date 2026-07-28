#version 330 core

in vec2 vUV;
out vec4 oColor;

uniform sampler2D uSource;
uniform vec2 uTexelSize;

void main() {
    vec2 t = uTexelSize;

    vec3 a = texture(uSource, vUV + vec2(-2.0 * t.x, 2.0 * t.y)).rgb;
    vec3 b = texture(uSource, vUV + vec2(0.0, 2.0 * t.y)).rgb;
    vec3 c = texture(uSource, vUV + vec2(2.0 * t.x, 2.0 * t.y)).rgb;
    vec3 d = texture(uSource, vUV + vec2(-2.0 * t.x, 0.0)).rgb;
    vec3 e = texture(uSource, vUV).rgb;
    vec3 f = texture(uSource, vUV + vec2(2.0 * t.x, 0.0)).rgb;
    vec3 g = texture(uSource, vUV + vec2(-2.0 * t.x, -2.0 * t.y)).rgb;
    vec3 h = texture(uSource, vUV + vec2(0.0, -2.0 * t.y)).rgb;
    vec3 i = texture(uSource, vUV + vec2(2.0 * t.x, -2.0 * t.y)).rgb;
    vec3 j = texture(uSource, vUV + vec2(-t.x, t.y)).rgb;
    vec3 k = texture(uSource, vUV + vec2(t.x, t.y)).rgb;
    vec3 l = texture(uSource, vUV + vec2(-t.x, -t.y)).rgb;
    vec3 m = texture(uSource, vUV + vec2(t.x, -t.y)).rgb;

    vec3 result = e * 0.125;
    result += (a + c + g + i) * 0.03125;
    result += (b + d + f + h) * 0.0625;
    result += (j + k + l + m) * 0.125;

    oColor = vec4(result, 1.0);
}
