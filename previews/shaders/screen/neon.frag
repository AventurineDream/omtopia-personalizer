#version 440
// Сгенерировано scripts/build-preview-shaders.py из shaders/neon.frag — не править руками.
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 fullSize;
    float time;
};
layout(binding = 1) uniform sampler2D tex;
#define v_texcoord qt_TexCoord0

// Neon: a light CRT-like layer for the Neon style — static scanlines locked to the pixel grid,
// a soft lift of bright pixels (they "glow" a bit against the darkened lines) and a gentle
// vignette. No `time` uniform and no warp: the picture does not move, so the cheapest damage
// tracking works and an idle screen costs nothing extra. Colours are not tinted.


const float LINES    = 0.10;  // how much every third row is darkened
const float GLOW     = 0.06;  // lift of bright pixels
const float VIGNETTE = 0.18;

void main() {
    vec4 c = texture(tex, v_texcoord);
    float row = mod(floor(gl_FragCoord.y), 3.0);
    float line = row == 0.0 ? 1.0 - LINES : 1.0;

    float luma = dot(c.rgb, vec3(0.299, 0.587, 0.114));
    vec3 rgb = c.rgb * line + GLOW * smoothstep(0.55, 1.0, luma) * c.rgb;

    vec2 d = v_texcoord - 0.5;
    rgb *= 1.0 - VIGNETTE * smoothstep(0.35, 0.75, length(d));
    fragColor = vec4(clamp(rgb, 0.0, 1.0), 1.0);
}
