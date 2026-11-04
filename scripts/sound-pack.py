#!/usr/bin/env python3
# Звуковые пакеты стилей: синтез с нуля (numpy → wav → ogg через ffmpeg), без чужих сэмплов.
#
#   python3 scripts/sound-pack.py [пакет ...]     # без аргументов — все пакеты
#
# События (scripts/play-sound.sh): open close switch special fullscreen lock power menu notify critical volume.
# Характер пакетов:
#   flat     — короткие чистые синус-тики                 glass  — стеклянные колокольчики (негармонические)
#   fluent   — мягкая маримба                             paper  — шорох листа, карандаш, постук
#   neumorph — приглушённые мягкие «тук»                  brutal — жёсткие клики и низкие удары
#   retro    — 8-битные квадраты, свои мотивы             neon   — синт-пила с проходом фильтра, хорус
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

SR = 48000
EVENTS = ("open", "close", "switch", "special", "fullscreen", "lock", "power", "menu", "notify", "critical", "volume")
RNG = np.random.default_rng(20261104)


# ── примитивы ────────────────────────────────────────────────────────────
def t_(dur):
    return np.arange(int(SR * dur)) / SR


def env(dur, attack=0.004, decay=None, curve=6.0):
    t = t_(dur)
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    d = np.exp(-curve * t / (decay or dur))
    return a * d


def note(f):
    """Частота по названию ноты: 'A4', 'C#5'."""
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    if isinstance(f, (int, float)):
        return float(f)
    n, o = f[:-1], int(f[-1])
    return 440.0 * 2 ** ((names[n] + 12 * (o - 4)) / 12)


def sine(f, dur, f_end=None):
    t = t_(dur)
    f0 = note(f)
    f1 = note(f_end) if f_end else f0
    freq = f0 + (f1 - f0) * t / dur
    return np.sin(2 * np.pi * np.cumsum(freq) / SR)


def partials(f, dur, ratios, amps, decays):
    t = t_(dur)
    out = np.zeros_like(t)
    for r, a, d in zip(ratios, amps, decays):
        out += a * np.sin(2 * np.pi * note(f) * r * t) * np.exp(-t / d)
    return out


def square(f, dur, duty=0.5):
    t = t_(dur)
    ph = (note(f) * t) % 1.0
    return np.where(ph < duty, 1.0, -1.0)


def saw(f, dur, detune=0.0):
    t = t_(dur)
    out = np.zeros_like(t)
    for d in (-detune, 0.0, detune):
        ph = (note(f) * (1 + d) * t) % 1.0
        out += 2 * ph - 1
    return out / 3


def lowpass(x, cutoff):
    """Однополюсный ФНЧ; cutoff — число или массив той же длины (проход фильтра)."""
    c = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    a = 1 - np.exp(-2 * np.pi * c / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def band(x, lo, hi):
    return lowpass(highpass(x, lo), hi)


def noise(dur):
    return RNG.uniform(-1, 1, int(SR * dur))


def seq(*parts, gap=0.0):
    """Подряд: (сигнал, задержка_начала) или сигналы друг за другом с паузой gap."""
    out = np.zeros(0)
    pos = 0
    for p in parts:
        if isinstance(p, tuple):
            sig, at = p
            start = int(SR * at)
        else:
            sig, start = p, pos
        end = start + len(sig)
        if end > len(out):
            out = np.pad(out, (0, end - len(out)))
        out[start:end] += sig
        pos = end + int(SR * gap)
    return out


def finish(x, peak=0.6, tail=0.02):
    # Срез постоянной составляющей (< 20 Гц): у низких квадратов она даёт «полку» и щелчки.
    x = highpass(np.pad(x, (0, int(SR * tail))), 20)
    fade = min(len(x), int(SR * 0.008))
    x[-fade:] *= np.linspace(1, 0, fade)
    m = np.max(np.abs(x)) or 1
    return x / m * peak


# ── пакеты ───────────────────────────────────────────────────────────────
def flat(ev):
    tick = lambda f, d=0.05: sine(f, d) * env(d, 0.002, d * 0.5)
    return {
        "open": seq(tick("E6"), (tick("A6"), 0.045)),
        "close": seq(tick("A6"), (tick("E6"), 0.045)),
        "switch": tick("C7", 0.035),
        "special": seq(tick("G6"), (tick("D7"), 0.05)),
        "fullscreen": seq(tick("C6"), (tick("G6"), 0.04), (tick("C7"), 0.08)),
        "lock": seq(tick("C7"), (tick("G6", 0.08), 0.06)),
        "power": seq(tick("G6", 0.08), (tick("C6", 0.12), 0.08)),
        "menu": tick("F6", 0.04),
        "notify": seq(tick("A6", 0.07), (tick("E7", 0.09), 0.07)),
        "critical": seq(tick("A6", 0.06), (tick("A6", 0.06), 0.1), (tick("A6", 0.06), 0.2)),
        "volume": tick("D7", 0.025),
    }[ev]


def glass(ev):
    R, A, D = (1, 2.76, 5.40, 8.93), (1, 0.5, 0.25, 0.12), (0.5, 0.25, 0.12, 0.06)
    bell = lambda f, d=0.6: partials(f, d, R, A, D) * env(d, 0.002, d, 3)
    return {
        "open": seq(bell("E6", 0.5), (bell("B6", 0.6), 0.07)),
        "close": seq(bell("B6", 0.5), (bell("E6", 0.6), 0.07)),
        "switch": bell("G6", 0.35),
        "special": seq(bell("D6"), (bell("A6"), 0.08), (bell("D7"), 0.16)),
        "fullscreen": seq(bell("C6", 0.5), (bell("G6", 0.5), 0.05), (bell("E7", 0.7), 0.1)),
        "lock": seq(bell("A6", 0.5), (bell("E6", 0.8), 0.12)),
        "power": seq(bell("E6", 0.7), (bell("B5", 0.8), 0.15), (bell("E5", 1.2), 0.3)),
        "menu": bell("C7", 0.3),
        "notify": seq(bell("G6", 0.6), (bell("D7", 0.8), 0.11)),
        "critical": seq(bell("F6", 0.4), (bell("F6", 0.4), 0.16), (bell("B5", 0.6), 0.32)),
        "volume": bell("E7", 0.2),
    }[ev]


def fluent(ev):
    R, A, D = (1, 3.93, 9.2), (1, 0.35, 0.12), (0.18, 0.05, 0.02)
    mar = lambda f, d=0.3: partials(f, d, R, A, D) * env(d, 0.003, d, 4)
    return {
        "open": seq(mar("C5"), (mar("G5"), 0.06)),
        "close": seq(mar("G5"), (mar("C5"), 0.06)),
        "switch": mar("E5", 0.2),
        "special": seq(mar("D5"), (mar("A5"), 0.07), (mar("F#5"), 0.14)),
        "fullscreen": seq(mar("C5"), (mar("E5"), 0.05), (mar("G5"), 0.1), (mar("C6", 0.4), 0.15)),
        "lock": seq(mar("G5"), (mar("D5", 0.4), 0.1)),
        "power": seq(mar("E5"), (mar("C5"), 0.12), (mar("G4", 0.6), 0.24)),
        "menu": mar("A5", 0.18),
        "notify": seq(mar("E5"), (mar("B5"), 0.09), (mar("E6", 0.4), 0.18)),
        "critical": seq(mar("C5"), (mar("F#5"), 0.12), (mar("C5"), 0.24), (mar("F#5"), 0.36)),
        "volume": mar("G5", 0.12),
    }[ev]


def paper(ev):
    def rustle(d=0.18, lo=1200, hi=6000, grains=40, k=1.0):
        x = np.zeros(int(SR * d))
        for _ in range(int(grains * k)):
            g = noise(RNG.uniform(0.004, 0.02))
            g *= np.hanning(len(g)) * RNG.uniform(0.2, 1)
            at = int(RNG.uniform(0, max(1, len(x) - len(g))))
            x[at:at + len(g)] += g
        return band(x, lo, hi) * env(d, 0.01, d, 2.5)

    def pencil(d=0.06):
        return band(noise(d), 2500, 9000) * env(d, 0.002, d * 0.6, 5) * (1 + 0.5 * np.sin(2 * np.pi * 90 * t_(d)))

    def tap(f="A3", d=0.08):
        return (sine(f, d) * 0.7 + band(noise(d), 300, 1500) * 0.6) * env(d, 0.001, d * 0.35)

    return {
        "open": rustle(0.2),
        "close": rustle(0.16, 900, 4000),
        "switch": pencil(0.045),
        "special": seq(pencil(0.05), (pencil(0.05), 0.08)),
        "fullscreen": rustle(0.32, 800, 5000, 70),
        "lock": seq(tap("E3"), (tap("A2", 0.12), 0.09)),
        "power": seq(rustle(0.25, 600, 3500), (tap("D3", 0.15), 0.22)),
        "menu": tap("C4", 0.06),
        "notify": seq(pencil(0.05), (pencil(0.04), 0.07), (tap("G3", 0.1), 0.14)),
        "critical": seq(tap("A3"), (tap("A3"), 0.13), (tap("A3"), 0.26), (pencil(0.08), 0.38)),
        "volume": pencil(0.025),
    }[ev]


def neumorph(ev):
    def thud(f="C3", d=0.12, f_end=None):
        x = sine(f, d, f_end or note(f) * 0.7)
        return lowpass(x, 900) * env(d, 0.012, d * 0.45, 4)

    return {
        "open": seq(thud("G3"), (thud("C4"), 0.07)),
        "close": seq(thud("C4"), (thud("G3"), 0.07)),
        "switch": thud("E3", 0.08),
        "special": seq(thud("D3"), (thud("A3"), 0.09)),
        "fullscreen": seq(thud("C3"), (thud("G3"), 0.06), (thud("C4", 0.18), 0.12)),
        "lock": seq(thud("A3"), (thud("D3", 0.2), 0.1)),
        "power": seq(thud("E3", 0.2), (thud("A2", 0.3), 0.16)),
        "menu": thud("F3", 0.07),
        "notify": seq(thud("C4"), (thud("G4", 0.16), 0.1)),
        "critical": seq(thud("D4"), (thud("D4"), 0.14), (thud("D4"), 0.28)),
        "volume": thud("A3", 0.05),
    }[ev]


def brutal(ev):
    def click(d=0.025):
        return np.clip(square("C6", d, 0.3) * env(d, 0.0005, d * 0.3) * 3, -1, 1)

    def thump(f="A1", d=0.18):
        x = sine(f, d, note(f) * 0.6) + 0.4 * square(f, d)
        return np.clip(lowpass(x, 600) * env(d, 0.001, d * 0.5) * 2.2, -1, 1)

    return {
        "open": seq(click(), (thump("D2", 0.12), 0.02)),
        "close": seq(thump("D2", 0.12), (click(), 0.1)),
        "switch": click(0.02),
        "special": seq(click(), (click(), 0.06), (thump("G1", 0.14), 0.1)),
        "fullscreen": seq(thump("A1", 0.25), (click(), 0.05)),
        "lock": seq(click(), (thump("E1", 0.3), 0.03)),
        "power": seq(thump("E1", 0.4), (thump("A0", 0.5), 0.25)),
        "menu": click(0.03),
        "notify": seq(click(), (click(), 0.08), (thump("C2", 0.15), 0.16)),
        "critical": seq(thump("A1", 0.1), (thump("A1", 0.1), 0.13), (thump("A1", 0.1), 0.26), (click(), 0.36)),
        "volume": click(0.015),
    }[ev]


def retro(ev):
    def bleep(f, d=0.06, duty=0.5):
        x = square(f, d, duty) * env(d, 0.001, d * 2, 2)
        return np.round(x * 7) / 7          # 3-битная амплитуда — «8-битное» зерно

    def run(notes, d=0.045, duty=0.5):
        return seq(*[(bleep(n, d, duty), i * d) for i, n in enumerate(notes)])

    return {
        "open": run(["C5", "E5", "G5"]),
        "close": run(["G5", "E5", "C5"]),
        "switch": bleep("A5", 0.035, 0.25),
        "special": run(["D5", "F#5", "A5", "D6"], 0.04, 0.25),
        "fullscreen": run(["C5", "G5", "C6", "G6"], 0.04),
        "lock": run(["G5", "D5"], 0.07, 0.25),
        "power": run(["E5", "C5", "A4", "E4"], 0.08),
        "menu": bleep("E6", 0.03, 0.125),
        "notify": run(["B5", "E6"], 0.07, 0.25),
        "critical": run(["F5", "B4", "F5", "B4", "F5"], 0.06, 0.5),
        "volume": bleep("C6", 0.02, 0.125),
    }[ev]


def neon(ev):
    def synth(f, d=0.25, sweep=(400, 5000), f_end=None):
        x = saw(f, d, 0.006) if not f_end else saw(f, d, 0.006) * 0.5 + 0.5 * sine(f, d, f_end)
        cut = np.geomspace(sweep[0], sweep[1], len(x))
        return lowpass(x, cut) * env(d, 0.01, d * 0.6, 3)

    def zap(d=0.08):
        return synth("A5", d, (8000, 600), "A3")

    return {
        "open": seq(synth("A4", 0.18), (synth("E5", 0.22), 0.07)),
        "close": seq(synth("E5", 0.18, (5000, 300)), (synth("A4", 0.22, (4000, 300)), 0.07)),
        "switch": zap(0.06),
        "special": seq(synth("D5", 0.15), (synth("A5", 0.15), 0.06), (synth("F#5", 0.3), 0.12)),
        "fullscreen": synth("A3", 0.45, (200, 9000), "A5"),
        "lock": seq(synth("E5", 0.2, (4000, 300)), (synth("A4", 0.35, (3000, 200)), 0.12)),
        "power": synth("A4", 0.7, (6000, 150), "A2"),
        "menu": zap(0.05),
        "notify": seq(synth("C#5", 0.18), (synth("G#5", 0.3), 0.09)),
        "critical": seq(zap(0.1), (zap(0.1), 0.13), (zap(0.1), 0.26), (synth("A3", 0.25, (3000, 200)), 0.38)),
        "volume": zap(0.03),
    }[ev]


PACKS = {"flat": flat, "glass": glass, "fluent": fluent, "paper": paper,
         "neumorph": neumorph, "brutal": brutal, "retro": retro, "neon": neon}
PEAK = {"brutal": 0.55, "neon": 0.5, "retro": 0.45}


def write_ogg(x, path, tmp):
    wav = os.path.join(tmp, "x.wav")
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "4", path], check=True)


def main():
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sounds")
    names = sys.argv[1:] or list(PACKS)
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            out = os.path.join(root, name)
            os.makedirs(out, exist_ok=True)
            for ev in EVENTS:
                write_ogg(finish(PACKS[name](ev), PEAK.get(name, 0.6)), os.path.join(out, ev + ".ogg"), tmp)
            print(name, len(EVENTS))


if __name__ == "__main__":
    main()
