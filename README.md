# Omarchy Customizer

[🇷🇺 Русский](README.ru.md)

One overlay for the whole look & feel of [Omarchy](https://omarchy.org): themes, wallpapers, Hyprland
animations, transparency, blur and screen shaders — with live preview while you browse. With the companion
plugins installed it also drives the bar, the lock screen, wallpaper transitions and the picker style.

![Desktop](screenshots/desktop.webp)

| Group | What's inside |
|---|---|
| **Presets** | Global desktop snapshots (bundled **DOT-MATRIX** preset + your own presets in `~/.config/omarchy/customizer/presets/*.json` with ★, `D` to delete, and automatic rollback to the previous setup) and **Style** — the form of the desktop on any theme: Flat, Glass, Fluent, DOT-MATRIX or your own (window geometry, bar, lock, launcher, widgets, OSD, notifications, animations, opacity, blur, sounds, Glyph, fonts; you choose which parts a style applies) |
| **Desktop** | Theme (palette + preview), Wallpaper (categories as in the background switcher), Recolor (any image into the current theme with lutgen), Dotify (LED dot-matrix wallpapers & Arch glyph generator), Wallpaper FX*, Widgets*, Dashboard* |
| **Bar*** | Bar Skin (plus “💾 Save the current skin” into `~/.config/omarchy/bar-skins/`, listed with ★; `D` deletes one after a confirmation), Bar Layout (own layouts the same way, in `~/.config/omarchy/bar-layouts/`), Bar Tweaks — 41 settings, each with its default and a live preview |
| **Windows** | Animations (18 presets), Transparency, Blur, OSD*, Notifications* (with tactile sound packs & Hyprland window/workspace sounds), Glyph (Nothing-inspired perimeter edge lighting & charger beams), Shader (CRT / TFT) |
| **Lock*** | Lock design with previews in the current theme, Lock Tweaks |
| **Pickers*** | Theme / wallpaper picker style, thumbnail cache, Launcher* skins |

\* appears only when the matching companion plugin is installed — see below.

| Bar | Windows |
| :---: | :---: |
| ![Bar](screenshots/bar.webp) | ![Windows](screenshots/windows.webp) |
| **Lock** | **Pickers** |
| ![Lock](screenshots/lock.webp) | ![Pickers](screenshots/pickers.webp) |

## Install

```sh
omarchy plugin add https://github.com/KamradSmeshnyavy/omarchy-customizer --enable
omarchy restart shell
```

Bind it in `~/.config/hypr/bindings.lua`:

```lua
o.bind("SUPER + SHIFT + T", "Omarchy Customizer", "omarchy-shell shell toggle kamradsmeshnyavy.customizer")
```

**Everything at once** — `install.sh` adds the Customizer and asks about each companion plugin (all through
`omarchy plugin add`), links the DOT-MATRIX fonts, binds **Super+Shift+T** in `~/.config/hypr/bindings.lua` and
restarts the shell. Read it before running:

```sh
curl -fsSLo /tmp/customizer-install.sh https://raw.githubusercontent.com/KamradSmeshnyavy/omarchy-customizer/main/install.sh
less /tmp/customizer-install.sh
bash /tmp/customizer-install.sh            # --all: every companion, --with bar,lock: only these, --none: just the Customizer
```

### Companion plugins

Each is a separate plugin; the Customizer finds them on its own.

| Plugin | Adds to the Customizer |
|---|---|
| [omarchy-bar-skins](https://github.com/KamradSmeshnyavy/omarchy-bar-skins) | **Bar** group: 20 skins (incl. `dotmatrix`), 10 layouts, compact mode, LED & glyph workspace styles |
| [omarchy-lock-designs](https://github.com/KamradSmeshnyavy/omarchy-lock-designs) | **Lock** group: 22 designs (incl. `dotmatrix`) |
| [omarchy-wallpaper-fx](https://github.com/KamradSmeshnyavy/omarchy-wallpaper-fx) | **Wallpaper FX**: 24 transitions with a preview |
| [omarchy-image-picker-styles](https://github.com/KamradSmeshnyavy/omarchy-image-picker-styles) | **Pickers** group: six picker styles |
| [omarchy-launcher-skins](https://github.com/KamradSmeshnyavy/omarchy-launcher-skins) | **Launcher** in Pickers: full-screen & hardware-bump (`dotmatrix`) launcher skins |
| [omarchy-desktop-widgets](https://github.com/KamradSmeshnyavy/omarchy-desktop-widgets) | **Widgets** and **Dashboard** in Desktop: desktop cards, DOT-MATRIX LED dashboard & Quick Settings drawer |
| [omarchy-edge-osd](https://github.com/KamradSmeshnyavy/omarchy-edge-osd) | **OSD** in Windows: volume and brightness at the screen edge (incl. DOT-MATRIX LED meter) |
| [omarchy-drawer-notifications](https://github.com/KamradSmeshnyavy/omarchy-drawer-notifications) | **Notifications** in Windows: drawer or DOT-MATRIX hardware toast cards + Glyph sweep hook |

### Optional programs

- `libvips` — fast thumbnails for themes and wallpapers (`omarchy pkg add libvips`)
- `zenity` — dialogs for colours, text and files in the tweaks
- `kamradsmeshnyavy.widgets` plugin — **Widgets** category in Desktop (clock, now playing, cava visualizer, system rings)
- `lutgen` — Recolor (shown only when both lutgen and zenity are there)
- `omarchy-wallpaper-theme` on `PATH` + `matugen` — “🎨 Theme from wallpaper” rows in **Theme**: a Material You theme `dynamic` built from the current wallpaper ([script](https://github.com/KamradSmeshnyavy/dotfiles/blob/main/omarchy-themes/scripts/omarchy-wallpaper-theme))

## Requirements

Omarchy 4 (Quattro) with its shell. Tested on Omarchy 4.0.6 with Quickshell 0.3.2.

- `jq` (ships with Omarchy).
- Optional: `libvips` (thumbnails), `zenity` (colour/text/file dialogs), `lutgen` (Recolor), `matugen` (theme from a wallpaper), `ffmpeg` and `pipewire` (`pw-play`) for sounds, `uv` (builds the Dotify fonts). Each feature hides itself when its program is missing.
- Companion plugins are optional — see the table above.

## Uninstall

```sh
omarchy plugin remove kamradsmeshnyavy.customizer
omarchy restart shell
```

If you used `install.sh`, also delete the Super+Shift+T line it added to `~/.config/hypr/bindings.lua` and the `~/.local/share/fonts/dotmatrix` link.

Your settings stay in `~/.config/omarchy/customizer.json`, `~/.config/omarchy/customizer/`, `~/.config/omarchy/style.json`, `~/.local/state/omarchy-customizer/`, `~/.local/state/hypr/{opacity,blur,screen-shader}` — delete them by hand if you don't need them.

## Keys

| Keys | |
|---|---|
| Tab / 1–6 | groups |
| j k · l ⏎ · h | move · open · back |
| / | search |
| h l, − + | change a tweak · x — reset it |
| p | play / show live (transitions, lock designs, picker) |
| r | surprise me |
| ? · q / Esc | all keys · close |

## How your choices survive a reload

The animation preset goes to `~/.local/state/omarchy-customizer/animations.lua`; transparency, blur and the
shader go to `~/.local/state/hypr/{opacity,blur,screen-shader}`. The Customizer re-applies them when the
shell starts and after every `hyprctl reload`. For a reload without even a flash of the defaults, load the
hook from your Hyprland config (e.g. at the end of `~/.config/hypr/looknfeel.lua`):

```lua
dofile(os.getenv("HOME") .. "/.config/omarchy/plugins/kamradsmeshnyavy.customizer/hypr/customizer.lua")
```

The scripts work on their own too — bind them if you like:

```lua
o.bind("SUPER + ALT + O", "Next transparency preset", "~/.config/omarchy/plugins/kamradsmeshnyavy.customizer/scripts/opacity.sh next")
o.bind("SUPER + ALT + U", "Next blur preset", "~/.config/omarchy/plugins/kamradsmeshnyavy.customizer/scripts/blur.sh next")
o.bind("SUPER + ALT + C", "Toggle screen shader", "~/.config/omarchy/plugins/kamradsmeshnyavy.customizer/scripts/crt-toggle.sh")
```

## Your own presets

- Desktop presets: `~/.config/omarchy/customizer/presets/*.json` (save directly from the **Presets** tab).
- Animations: `~/.config/omarchy/customizer/animations/*.lua` (Hyprland Lua: `hl.curve`, `hl.animation`).
  A file with the same name as a bundled preset replaces it.
- Shaders: `~/.config/omarchy/customizer/shaders/*.frag`. A shader that uses `time` gets
  `damage_tracking = 0` automatically, a warping one `1`.

## Windows and widgets

**Windows → Windows**: gaps between windows and to the screen edges, border width, Omarchy's "no gaps",
rounding of all windows, shadow and its size, dimming of inactive windows, the tiling layout (dwindle / master) and
window corners — `~/.config/omarchy/customizer/windows.json`, applied by `hypr/customizer.lua` on top of the style
geometry (a style writes its geometry there too), with a live mini-screen preview. **Desktop → Widgets** shows the
layout of the enabled widgets on a mini desktop and marks overlapping ones in red. The overlay opens on a given tab
with a payload: `omarchy-shell shell toggle kamradsmeshnyavy.customizer '{"category":"windows"}'`.

## Styles

Theme = colours and wallpaper, **style** = form, preset = theme + style + wallpaper. A style is a preset file
without `theme` / `wallpaper` plus `fonts` (an `omarchy-font-profile` profile). Its sections are merged into your
current settings, so it changes how things look, not which widgets are shown. Bundled styles live in
`styles/`, your own in `~/.config/omarchy/customizer/styles/*.json` (★, `D` to delete; "Save current look as a
style" in the **Style** tab). The switches below the list (`~/.config/omarchy/customizer/style-apply.json`)
choose what a style applies. A preset may reference a style with `"style": "<id>"`: the style is applied first,
then the preset's own fields on top. Rollback is the same "Restore previous setup" row in **Presets**.

A style's `look` block goes to `~/.config/omarchy/style.json` with the style id — panel tokens (shadows, animation
speed, material, corners, typeface) for `BarStyle.qml` in omarchy-desktop-widgets, omarchy-edge-osd and
omarchy-drawer-notifications.

**Neumorphism, Brutalism, Retro 9x, Neon** — panels drawn with their own material (soft relief, thick border
with a hard shadow, 3D bevel, accent glow), matching bar skins (`soft`, `brutal`, `bevel`, `neon`), theme pairs, sound packs,
GTK / Firefox looks; Neon adds the `neon` scanline shader, Retro the `retro` pixel font profile.

**Paper** — sheets of paper instead of panels (torn bottom edge, grain, a strip of tape in the accent colour),
handwritten [Caveat](https://github.com/googlefonts/caveat) (OFL, bundled in `fonts/`), the `paper` bar skin and the
`paper` screen shader (static grain over the whole screen, windows included; no `time` uniform, cheapest damage
tracking). Colours stay the theme's: a light theme gives white paper, a dark one — kraft / slate. The grain tile is
generated by `scripts/paper-texture.py` (`textures/paper.png` for light panels, `paper-dark.png` for dark ones).

`python3 scripts/check-styles.py` checks that every style sets the same knobs.

Every style sets every form knob (the bundled ones share one key set), so switching between any two styles is
complete. `hyprGeometry.noGaps` drives Omarchy's "no gaps" toggle (it also removes window borders): DOT-MATRIX turns it
on so windows sit flush against the bezel frame, every other style — and a preset with `"hyprGeometry": null` —
turns it off and the borders come back.

## Language

English and Russian. The language comes from `"lang"` in `~/.config/omarchy/customizer.json`, otherwise
from `$LANG` (`ru*` → Russian). Translations live in `i18n/<lang>.json`: the English string is the key —
a new language is one more file.

## License

GPL-3.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). The animation presets come from
[HyDE](https://github.com/HyDE-Project/HyDE), [ML4W](https://github.com/mylinuxforwork/dotfiles),
[end-4](https://github.com/end-4/dots-hyprland) and [DOT-MATRIX](https://github.com/poligle/Nihil-Shell)
([credits](animations/CREDITS.md)); Dotify, Glyph lighting and DOT-MATRIX sound packs are ported from
[DOT-MATRIX](https://github.com/poligle/Nihil-Shell) (MIT, Pol Iglesias); the overlay follows the
style of [Omarchy](https://github.com/basecamp/omarchy)'s own shell plugins (MIT).

Part of [my dotfiles](https://github.com/KamradSmeshnyavy/dotfiles).
