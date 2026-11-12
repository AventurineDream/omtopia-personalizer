#version 300 es
precision highp float;

// Reading: the screen as a printed page — monochrome ink on warm paper (scripts/reading-mode.sh).
// Brightness goes through a soft S-curve (text gets darker, page whiter), the result is mapped
// between INK and PAPER, then paper grain, a light 4×4 ordered dither (kills banding on the
// paper tone) and a faint vignette are added. Everything is locked to the pixel grid and there
// is no `time` uniform: the cheapest damage tracking works and an idle page costs nothing.

in vec2 v_texcoord;
uniform sampler2D tex;
layout(location = 0) out vec4 fragColor;

const vec3  INK      = vec3(0.11, 0.105, 0.12);
const vec3  PAPER    = vec3(0.945, 0.925, 0.87);
const float CONTRAST = 1.35;   // S-curve strength around the mid tone
const float LIFT     = 0.04;   // lifts dark UI a little so it doesn't turn into ink blobs
const float GRAIN    = 0.030;
const float BLOTCH   = 0.020;
const float DITHER   = 1.0 / 255.0;
const float VIGNETTE = 0.10;

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
    int i = q.x + q.y * 4;
    int m[16] = int[16](0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5);
    return float(m[i]) / 16.0 - 0.5;
}

void main() {
    vec3 c = texture(tex, v_texcoord).rgb;
    vec2 px = floor(gl_FragCoord.xy);

    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    l = LIFT + (1.0 - LIFT) * l;
    // Symmetric S-curve: pow on both halves around 0.5.
    float s = l < 0.5 ? 0.5 * pow(2.0 * l, CONTRAST) : 1.0 - 0.5 * pow(2.0 - 2.0 * l, CONTRAST);

    vec3 rgb = mix(INK, PAPER, s);

    float grain = hash12(px) - 0.5;
    float blotch = valueNoise(px / 180.0) + 0.5 * valueNoise(px / 60.0) - 0.75;
    rgb *= 1.0 + s * (GRAIN * grain + BLOTCH * blotch);
    rgb += DITHER * bayer4(px);

    vec2 d = v_texcoord - 0.5;
    rgb *= 1.0 - VIGNETTE * smoothstep(0.25, 0.75, dot(d, d) * 2.0);

    fragColor = vec4(clamp(rgb, 0.0, 1.0), 1.0);
}
