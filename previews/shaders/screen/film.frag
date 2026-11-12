#version 440
// Сгенерировано scripts/build-preview-shaders.py из shaders/film.frag — не править руками.
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

// Film: black-and-white film stock — luminance with a filmic toe/shoulder, static silver grain
// that is strongest in the mid tones, and a soft vignette. No `time`: the grain is frozen, so an
// idle screen costs nothing extra.


const float GRAIN    = 0.08;
const float VIGNETTE = 0.22;
const vec3  TINT     = vec3(1.0, 0.985, 0.95);  // slightly warm paper base of the print

float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

void main() {
    vec3 c = texture(tex, v_texcoord).rgb;
    vec2 px = floor(gl_FragCoord.xy);

    // Orange-filter style weighting (darker blues, brighter skin/reds), then a filmic curve.
    float l = dot(c, vec3(0.36, 0.56, 0.08));
    l = l * l * (3.0 - 2.0 * l);

    // Two octaves of grain: fine per pixel plus 2×2 clumps.
    float g = (hash12(px) - 0.5) + 0.6 * (hash12(floor(px / 2.0) + 17.0) - 0.5);
    l += GRAIN * g * 4.0 * l * (1.0 - l);

    vec2 d = v_texcoord - 0.5;
    l *= 1.0 - VIGNETTE * smoothstep(0.2, 0.8, dot(d, d) * 2.0);

    fragColor = vec4(clamp(l * TINT, 0.0, 1.0), 1.0);
}
