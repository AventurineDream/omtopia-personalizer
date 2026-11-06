#!/usr/bin/python3 -I
"""Qt-варианты экранных шейдеров для превью в Customizer.

  /usr/bin/python3 -I scripts/build-preview-shaders.py

Каждый shaders/<имя>.frag (GLSL 300 es для Hyprland: v_texcoord, tex, fullSize, time) переписывается в
previews/shaders/screen/<имя>.frag (#version 440 с uniform-блоком ShaderEffect) и компилируется
`qsb --qt6` в <имя>.frag.qsb. Тело шейдера не меняется. Не собрался — сообщает и идёт дальше
(превью такого шейдера покажет код). Запускать после правки shaders/*.frag; результат коммитится."""
import os
import re
import subprocess
import sys

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PLUGIN, "shaders")
OUT = os.path.join(PLUGIN, "previews/shaders/screen")
QSB = "/usr/lib/qt6/bin/qsb"

HEADER = """#version 440
// Сгенерировано scripts/build-preview-shaders.py из shaders/{name}.frag — не править руками.
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {{
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 fullSize;
    float time;
}};
layout(binding = 1) uniform sampler2D tex;
#define v_texcoord qt_TexCoord0
"""

DROP = [
    r"^\s*#version\b.*$",
    r"^\s*precision\s+\w+\s+float\s*;.*$",
    r"^\s*(in|varying)\s+vec2\s+v_texcoord\s*;.*$",
    r"^\s*uniform\s+sampler2D\s+tex\s*;.*$",
    r"^\s*uniform\s+vec2\s+fullSize\s*;.*$",
    r"^\s*uniform\s+float\s+time\s*;.*$",
    r"^\s*layout\s*\(\s*location\s*=\s*0\s*\)\s*out\s+vec4\s+fragColor\s*;.*$",
]


def convert(name, text):
    lines = [ln for ln in text.split("\n") if not any(re.match(p, ln) for p in DROP)]
    body = "\n".join(lines).replace("texture2D(", "texture(")
    return HEADER.format(name=name) + body


def main():
    os.makedirs(OUT, exist_ok=True)
    bad = 0
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".frag"):
            continue
        name = f[:-5]
        dst = os.path.join(OUT, f)
        with open(os.path.join(SRC, f)) as fh:
            src = fh.read()
        with open(dst, "w") as fh:
            fh.write(convert(name, src))
        p = subprocess.run([QSB, "--qt6", "-o", dst + ".qsb", dst], capture_output=True, text=True)
        if p.returncode != 0:
            bad += 1
            print(f"FAIL {name}: {p.stderr.strip()[:300]}")
        else:
            uses_time = bool(re.search(r"^\s*uniform\s+float\s+time\s*;", src, re.M))
            print(f"ok   {name}{'  (time)' if uses_time else ''}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
