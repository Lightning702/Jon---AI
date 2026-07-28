#version 330 core

in vec2 vUV;
in vec4 vColor;
out vec4 oColor;

uniform sampler2D uTexture;
uniform int uMode;
uniform float uSmoothing;
uniform float uTime;

void main() {
    if (uMode == 0) {
        oColor = vColor;
    } else if (uMode == 1) {
        float d = texture(uTexture, vUV).r;
        float w = fwidth(d) * 0.9 + uSmoothing;
        float a = smoothstep(0.5 - w, 0.5 + w, d);
        oColor = vec4(vColor.rgb, vColor.a * a);
    } else if (uMode == 2) {
        vec4 t = texture(uTexture, vUV);
        oColor = t * vColor;
    } else {
        float d = texture(uTexture, vUV).r;
        float w = fwidth(d) * 0.9 + uSmoothing;
        float outline = smoothstep(0.26 - w, 0.26 + w, d);
        float fill = smoothstep(0.5 - w, 0.5 + w, d);
        vec3 c = mix(vec3(0.0), vColor.rgb, fill);
        oColor = vec4(c, vColor.a * outline);
    }
}
