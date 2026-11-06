#version 440
// Живое превью Dotify: тот же рисунок, что render() в scripts/dotify.py, но на GPU и сразу.
// Ячейка pitch×pitch; яркость — среднее яркости по ячейке (4×4 выборки) с чёрной точкой 0.10
// и степенью gamma; «звёзды» — по максимуму (порог 0.55, усиление 0.9). В каждой ячейке —
// «выключенный» диод (r = 0.16·pitch, уровень offLevel) и горящий (r = 0.44·pitch·(0.25 + 0.75·√v),
// серый 30 + 206·v). Маска 0…1 смешивает background и tint. Растяжка по перцентилям из dotify.py
// не переносится — превью чуть темнее на тусклых картинках.
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 size;        // размер элемента, px
    float pitch;      // шаг ячейки, px
    float gamma;
    float offLevel;
    vec4 tint;
    vec4 background;
};

layout(binding = 1) uniform sampler2D source;

float luma(vec2 p) {
    vec3 c = texture(source, p / size).rgb;
    return dot(c, vec3(0.2126, 0.7152, 0.0722));
}

void main() {
    vec2 px = qt_TexCoord0 * size;
    vec2 cells = floor(size / pitch);
    vec2 origin = floor((size - cells * pitch) * 0.5);
    vec2 cell = floor((px - origin) / pitch);
    if (any(lessThan(cell, vec2(0.0))) || any(greaterThanEqual(cell, cells))) {
        fragColor = background * qt_Opacity;
        return;
    }

    float sum = 0.0;
    float peak = 0.0;
    for (int j = 0; j < 4; ++j) {
        for (int i = 0; i < 4; ++i) {
            float l = luma(origin + (cell + (vec2(float(i), float(j)) + 0.5) / 4.0) * pitch);
            sum += l;
            peak = max(peak, l);
        }
    }
    float level = pow(clamp((sum / 16.0 - 0.10) / 0.90, 0.0, 1.0), gamma);
    level = max(level, 0.9 * clamp((peak - 0.55) / 0.45, 0.0, 1.0));

    vec2 center = origin + (cell + 0.5) * pitch;
    float d = length(px - center);
    float aa = 0.6;
    float rOff = 0.16 * pitch;
    float mask = offLevel * (1.0 - smoothstep(rOff - aa, rOff + aa, d));
    if (level > 0.02) {
        float r = 0.44 * pitch * (0.25 + 0.75 * sqrt(level));
        float grey = (30.0 + 206.0 * level) / 255.0;
        mask = max(mask, grey * (1.0 - smoothstep(r - aa, r + aa, d)));
    }
    fragColor = mix(background, tint, mask) * qt_Opacity;
}
