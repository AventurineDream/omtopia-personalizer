#version 440
// Сгенерировано scripts/build-preview-shaders.py из shaders/gameboy.frag — не править руками.
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

// Game Boy: four shades of green with a 4×4 ordered dither and a faint LCD pixel grid.
// Static (no `time`, no warp) — cheapest damage tracking.


const float PIXEL = 3.0;   // size of one "LCD dot" in physical pixels
const float GRID  = 0.10;  // darkening of the gaps between dots

float bayer4(vec2 p) {
    ivec2 q = ivec2(mod(p, 4.0));
    int m[16] = int[16](0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5);
    return float(m[q.x + q.y * 4]) / 16.0 - 0.5;
}

void main() {
    vec2 res = fullSize;
    // Work in texture pixels (v_texcoord), not gl_FragCoord: their y axes may be flipped.
    vec2 p = v_texcoord * res;
    vec2 cell = floor(p / PIXEL);
    // Sample the centre of the dot so text stays readable, just chunkier.
    vec3 c = texture(tex, (cell + 0.5) * PIXEL / res).rgb;

    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    float q = clamp(floor(l * 3.0 + 0.5 + 0.55 * bayer4(cell)), 0.0, 3.0);

    vec3 pal[4] = vec3[4](vec3(0.06, 0.22, 0.06), vec3(0.19, 0.38, 0.19),
                          vec3(0.55, 0.67, 0.06), vec3(0.61, 0.74, 0.06));
    vec3 rgb = pal[int(q)];

    vec2 f = fract(p / PIXEL);
    float edge = step(f.x, 1.0 / PIXEL) + step(f.y, 1.0 / PIXEL);
    rgb *= 1.0 - GRID * min(edge, 1.0);

    fragColor = vec4(rgb, 1.0);
}
