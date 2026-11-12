#version 300 es
precision highp float;

// Reading: the screen as a printed page — monochrome ink on warm paper (scripts/reading-mode.sh).
// Brightness goes through an e-ink response curve (gamma + S-curve + a small mid-tone lift), the
// result is mapped between INK and PAPER, then paper texture is laid only where the page is bright:
// multi-scale grain, directional fibres, a 4×4 ordered dither and a slight warm colour drift. A faint
// vignette darkens the edges like a sheet. Everything is locked to the pixel grid and there is no
// `time` uniform: the cheapest damage tracking works and an idle page costs nothing.
//
// INVERT = 1 reads a dark theme as a page (light background ↔ dark text), so reading mode does not
// need a slow theme switch; photos then look like negatives. reading-mode.sh writes a copy with the
// chosen INVERT / TEXTURE to ~/.local/state/hypr/reading-page.frag — keep both lines exactly as is.

in vec2 v_texcoord;
uniform sampler2D tex;
layout(location = 0) out vec4 fragColor;

const float INVERT  = 0.0;
const float TEXTURE = 1.0;

const vec3  INK      = vec3(0.10, 0.10, 0.12);
const vec3  PAPER    = vec3(0.94, 0.92, 0.86);
const float GAMMA    = 1.2;    // e-ink: ink clumps, mid tones go a bit darker
const float MIDBOOST = 0.08;   // ...and the mid tones get a small lift back so UI greys stay apart
const float GRAIN    = 0.035;
const float FIBRE    = 0.025;
const float DITHER   = 0.025;
const float WARMTH   = 0.02;
const float VIGNETTE = 0.12;

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

// 4×4 Bayer matrix, 0..15 → -0.5..0.5
float bayer4(vec2 p) {
    ivec2 q = ivec2(mod(p, 4.0));
    int m[16] = int[16](0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5);
    return float(m[q.x + q.y * 4]) / 16.0 - 0.5;
}

void main() {
    vec3 c = texture(tex, v_texcoord).rgb;
    vec2 px = floor(gl_FragCoord.xy);

    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    l = mix(l, 1.0 - l, INVERT);
    l = pow(l, GAMMA);
    l = smoothstep(0.06, 0.94, l);
    l += MIDBOOST * smoothstep(0.3, 0.5, l) * (1.0 - smoothstep(0.5, 0.7, l));

    // Texture lives on the paper, not on the ink: text edges stay clean.
    float paper = smoothstep(0.5, 0.95, l) * TEXTURE;
    float grain = valueNoise(px / 3.0) * 0.5 + hash12(px) * 0.5 - 0.5;
    // Fibres: noise stretched along one direction, so the sheet has a "grain direction".
    float fibre = valueNoise(vec2(px.x * 0.35 + px.y * 0.15, px.y * 0.05 - px.x * 0.02)) - 0.5;
    l += paper * (GRAIN * grain + FIBRE * fibre + DITHER * bayer4(px));

    vec2 d = v_texcoord - 0.5;
    l *= 1.0 - VIGNETTE * smoothstep(0.25, 0.75, dot(d, d) * 2.0);
    l = clamp(l, 0.0, 1.0);

    // Slightly uneven warmth of the sheet, ~25 px blotches.
    float w = (valueNoise(px / 25.0) - 0.5) * WARMTH * TEXTURE;
    vec3 sheet = PAPER + vec3(w, 0.5 * w, -0.2 * w);

    fragColor = vec4(mix(INK, sheet, l), 1.0);
}
