# Omarchy Customizer

[🇷🇺 Русский](README.ru.md)

One overlay for the whole look & feel of [Omarchy](https://omarchy.org): themes, wallpapers, Hyprland
animations, transparency, blur and screen shaders — with live preview while you browse. With the companion
plugins installed it also drives the bar, the lock screen, wallpaper transitions and the picker style.

The window is laid out like a Material 3 settings app: a navigation rail (Home + the groups below), a page with
breadcrumbs, a title, search across every setting and the group's tabs, a live-preview card on top, and below it
setting cards — switches, segmented buttons, sliders, colour swatches — or a gallery of tiles. Home shows what is in
use right now and quick actions. It follows the theme, the glass / solid material and the DOT-MATRIX style.

![Customizer](screenshots/home.webp)

<!-- Demo video: repo-videos/omarchy-customizer.mp4 — drag it here when editing this file on GitHub -->

| Group | What's inside |
|---|---|
| **Presets** | Global desktop snapshots (bundled **DOT-MATRIX** preset + your own presets in `~/.config/omarchy/customizer/presets/*.json` with ★, `D` to delete, and automatic rollback to the previous setup) and **Style** — the form of the desktop on any theme: Flat, Glass, Fluent, DOT-MATRIX or your own (window geometry, bar, lock, launcher, widgets, OSD, notifications, animations, opacity, blur, sounds, Glyph, fonts; you choose which parts a style applies) |
| **Desktop** | Theme (palette + preview), Wallpaper (categories as in the background switcher), Recolor (any image into the current theme with lutgen), Dotify (LED dot-matrix wallpapers & Arch glyph generator), Wallpaper FX*, Widgets*, Dashboard* |
| **Bar*** | Bar Skin (plus “💾 Save the current skin” into `~/.config/omarchy/bar-skins/`, listed with ★; `D` deletes one after a confirmation), Bar Layout (own layouts the same way, in `~/.config/omarchy/bar-layouts/`), Bar Tweaks — 41 settings, each with its default and a live preview |
| **Windows** | Animations (18 presets), Transparency, Blur, OSD*, Notifications* (with tactile sound packs & Hyprland window/workspace sounds), Glyph (Nothing-inspired perimeter edge lighting & charger beams), Shader (CRT / TFT / reading / film / Game Boy) |
| **Lock*** | Lock design with previews in the current theme, Lock Tweaks |
| **Pickers*** | Theme / wallpaper picker style, thumbnail cache, Launcher* skins (live preview of the real skin in the card) |

\* appears only when the matching companion plugin is installed — see below.

| Theme | Wallpaper (favourites, `D` to trash) |
| :---: | :---: |
| ![Theme](screenshots/themes.webp) | ![Wallpaper](screenshots/wallpaper.webp) |
| **Style — live scene, `z` full size** | **Bar skin** |
| ![Style](screenshots/styles-full.webp) | ![Bar skin](screenshots/bar-skins.webp) |
| **Animations — the curves play in the card** | **Screen shaders** |
| ![Animations](screenshots/anims.webp) | ![Shaders](screenshots/shaders.webp) |
| **Launcher — the real skin, live** | **Fonts** |
| ![Launcher](screenshots/launcher-full.webp) | ![Fonts](screenshots/fonts.webp) |
| **Search across every setting** | **Dotify in DOT-MATRIX** |
| ![Search](screenshots/search.webp) | ![Dotify](screenshots/dotmatrix-dotify.webp) |

The window follows the style: Glass, Paper and DOT-MATRIX —

![Styles](screenshots/styles.webp)

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
restarts the shell. It ships with the plugin — read it, then run it:

```sh
less ~/.config/omarchy/plugins/kamradsmeshnyavy.customizer/install.sh
bash ~/.config/omarchy/plugins/kamradsmeshnyavy.customizer/install.sh            # --all: every companion, --with bar,lock: only these, --none: just the Customizer
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

- `libvips` — fast thumbnails for themes and wallpapers (package `libvips`)
- `zenity` — dialogs for colours, text and files in the tweaks
- `kamradsmeshnyavy.widgets` plugin — **Widgets** category in Desktop (clock, now playing, cava visualizer, system rings)
- `lutgen` — Recolor (shown only when both lutgen and zenity are there)
- `omarchy-wallpaper-theme` on `PATH` + `matugen` — “🎨 Theme from wallpaper” rows in **Theme**: a Material You theme `dynamic` built from the current wallpaper ([script](https://github.com/KamradSmeshnyavy/dotfiles/blob/main/omarchy-themes/scripts/omarchy-wallpaper-theme))

## Requirements

Omarchy 4 (Quattro) with its shell. Tested on Omarchy 4.0.6 with Quickshell 0.3.2.

- `python3` and `jq` (both ship with Omarchy).
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
| j k · h l | move · rail ⇄ page (in a gallery h l move between tiles) |
| Tab / ⇧Tab · 0 · 1–6 | next / previous tab · Home · rail section |
| ⏎ | apply · toggle · open |
| h l, − + | change a setting · x — reset it · i — type a value |
| / | search all settings (↑↓ pick a result in another section, ⏎ go there) |
| v · z · n · J K | hide the preview · preview at full size · description over it · scroll the description |
| f | favourite theme / wallpaper (Themes, Wallpaper) |
| D | delete your own preset / style / bar skin / layout; in Wallpaper — your own wallpaper to the trash (asks in the window) |
| p | play / show live (transitions, lock designs, picker); in Launcher — open it with the skin under the cursor, back to Customizer on close |
| r | surprise me |
| ? · q / Esc | all keys · close |

Everything also works with the mouse: drag sliders, click switches, segments and tiles. Keys work in any keyboard layout (they follow the physical key, like in the US layout); typing in search stays as typed.

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
o.bind("SUPER + ALT + R", "Toggle reading mode", "~/.config/omarchy/plugins/kamradsmeshnyavy.customizer/scripts/reading-mode.sh")
```

## Reading mode

`scripts/reading-mode.sh` (toggle / on / off / status) turns the desktop into a printed page for long reading:
the `reading` screen shader (monochrome ink on warm paper, paper grain, 4×4 ordered dither, faint vignette; static,
cheapest damage tracking), flat windows (no gaps, 1 px border, square corners, no blur / shadow) and no animations.
Optionally it sets the screen brightness and an Omarchy theme for the time of reading and puts them back afterwards.
Turning it off just reloads Hyprland: `hypr/customizer.lua` re-applies your style, the Windows tab and screen shader,
and keeps the page while the state file exists, so a config reload doesn't end reading. Settings —
`~/.config/omarchy/customizer/reading-mode.json`: `shader` (any shader name, `""` = none), `flat`, `animations`,
`brightness` (1–100, `0` = don't touch), `theme` (`""` = keep). Inspired by the reading mode of
[surface-dots](https://github.com/snes19xx/surface-dots); the code is our own.

New screen shaders: `reading`, `film` (black-and-white film: filmic curve, frozen silver grain, vignette) and
`gameboy` (four greens, ordered dither, LCD grid).

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

## How it works

- **Overlay** — `Customizer.qml` with its pieces in `ui/` (cards, controls, rail, tabs) and `previews/` (live scenes:
  bar, windows, styles, animations, screen shaders, Dotify LED matrix, OSD, notifications, dashboard, lock, Glyph,
  sounds).
- **Backend** — Python, standard library only: `backend/customizer/`. While the overlay is open it talks to one
  process (`backend/run.py serve`, JSON lines over stdin/stdout); the process exits when the overlay closes, so a
  closed Customizer costs nothing and an idle open one sleeps in `read()`. A step plus list reload takes ~2 ms.
  `customizer.sh <command> …` is a thin wrapper for everything else (theme hook, menu, fzf script).
- **Settings file** — every setting (type, limits, default, label, file it writes) is described in
  [`settings.json`](settings.json), one table per settings file. Labels are English; `i18n/<lang>.json` translates.
- **Tests** — `tests/compare_*.py` run the backend against the previous bash implementation
  (`tests/legacy/customizer.sh`) in a throw-away sandbox HOME with stubbed `hyprctl`/`omarchy-shell`/`zenity`:
  lists, commands, every setting step and every `apply` must match byte for byte. Commands the bash version never had
  (`wall-delete`, `launcher-open` with skin and return) are covered by `tests/test_new_commands.py`.
- **Screen shader previews** — `scripts/build-preview-shaders.py` turns `shaders/*.frag` into Qt versions in
  `previews/shaders/screen/` (run it after editing a shader).

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
