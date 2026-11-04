#version 300 es
precision highp float;

// Paper: a sheet of paper under the whole screen, windows included (the Paper style).
// Static grain locked to the physical pixel grid, soft blotches of uneven paper density
// and rare fibres. No `time` uniform and no warp: the image does not move, so the
// cheapest damage tracking works and an idle screen costs nothing extra.
// Colours are not tinted — the theme stays the theme; the grain only darkens / lightens
// a little, more on bright pixels (paper) than on dark ones (ink, dark themes).

in vec2 v_texcoord;
uniform sampler2D tex;
layout(location = 0) out vec4 fragColor;

const float GRAIN  = 0.035;  // fine grain
const float BLOTCH = 0.030;  // uneven density, ~200 px
const float FIBRE  = 0.045;  // rare fibres

// Dave Hoskins' hash12 — sin-free, stable on every GPU.
float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

float valueNoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash12(i), hash12(i + vec2(1.0, 0.0)), u.x),
               mix(hash12(i + vec2(0.0, 1.0)), hash12(i + vec2(1.0, 1.0)), u.x), u.y);
}

void main() {
    vec4 c = texture(tex, v_texcoord);
    vec2 px = floor(gl_FragCoord.xy);

    float grain = hash12(px) - 0.5;
    float blotch = valueNoise(px / 200.0) + 0.5 * valueNoise(px / 70.0) - 0.75;
    // Fibres: thin bright streaks where a stretched noise crosses a narrow band.
    float f = valueNoise(vec2(px.x / 9.0 + px.y / 31.0, px.y / 9.0 - px.x / 37.0));
    float fibre = smoothstep(0.985, 1.0, f);

    float luma = dot(c.rgb, vec3(0.299, 0.587, 0.114));
    float k = mix(0.45, 1.0, luma);
    vec3 rgb = c.rgb * (1.0 + k * (GRAIN * grain + BLOTCH * blotch)) - k * FIBRE * fibre;
    fragColor = vec4(clamp(rgb, 0.0, 1.0), 1.0);
}
