# Omarchy Customizer

[🇷🇺 Русский](README.ru.md)

One overlay for the whole look & feel of [Omarchy](https://omarchy.org): themes, wallpapers, Hyprland
animations, transparency, blur and screen shaders — with live preview while you browse. With the companion
plugins installed it also drives the bar, the lock screen, wallpaper transitions and the picker style.

![Desktop](screenshots/desktop.webp)

| Group | What's inside |
|---|---|
| **Presets** | Global desktop snapshots (bundled **NIHIL** preset + your own presets in `~/.config/omarchy/customizer/presets/*.json` with ★, `D` to delete, and automatic rollback to the previous setup) |
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

Customizer, plus a question for each companion plugin:

```sh
curl -fsSL https://raw.githubusercontent.com/KamradSmeshnyavy/omarchy-customizer/main/install.sh | bash
```

`… | bash -s -- --all` installs every companion, `--with bar,lock` only the listed ones, `--none` just the
Customizer. The script adds each plugin with `omarchy plugin add`, binds **Super+Shift+T** in
`~/.config/hypr/bindings.lua` and restarts the shell.

By hand:

```sh
omarchy plugin add https://github.com/KamradSmeshnyavy/omarchy-customizer --enable
omarchy restart shell
```

and bind it in `~/.config/hypr/bindings.lua`:

```lua
o.bind("SUPER + SHIFT + T", "Omarchy Customizer", "omarchy-shell shell toggle kamradsmeshnyavy.customizer")
```

Tested on Omarchy 4.0.6 with Quickshell 0.3.2.

### Companion plugins

Each is a separate plugin; the Customizer finds them on its own.

| Plugin | Adds to the Customizer |
|---|---|
| [omarchy-bar-skins](https://github.com/KamradSmeshnyavy/omarchy-bar-skins) | **Bar** group: 20 skins (incl. `nihil`), 10 layouts, compact mode, LED & glyph workspace styles |
| [omarchy-lock-designs](https://github.com/KamradSmeshnyavy/omarchy-lock-designs) | **Lock** group: 22 designs (incl. `nihil`) |
| [omarchy-wallpaper-fx](https://github.com/KamradSmeshnyavy/omarchy-wallpaper-fx) | **Wallpaper FX**: 24 transitions with a preview |
| [omarchy-image-picker-styles](https://github.com/KamradSmeshnyavy/omarchy-image-picker-styles) | **Pickers** group: six picker styles |
| [omarchy-launcher-skins](https://github.com/KamradSmeshnyavy/omarchy-launcher-skins) | **Launcher** in Pickers: full-screen & hardware-bump (`nihil`) launcher skins |
| [omarchy-desktop-widgets](https://github.com/KamradSmeshnyavy/omarchy-desktop-widgets) | **Widgets** and **Dashboard** in Desktop: desktop cards, NIHIL LED dashboard & Quick Settings drawer |
| [omarchy-edge-osd](https://github.com/KamradSmeshnyavy/omarchy-edge-osd) | **OSD** in Windows: volume and brightness at the screen edge (incl. NIHIL LED meter) |
| [omarchy-drawer-notifications](https://github.com/KamradSmeshnyavy/omarchy-drawer-notifications) | **Notifications** in Windows: drawer or NIHIL hardware toast cards + Glyph sweep hook |

### Optional programs

- `libvips` — fast thumbnails for themes and wallpapers (`omarchy pkg add libvips`)
- `zenity` — dialogs for colours, text and files in the tweaks
- `kamradsmeshnyavy.widgets` plugin — **Widgets** category in Desktop (clock, now playing, cava visualizer, system rings)
- `lutgen` — Recolor (shown only when both lutgen and zenity are there)
- `omarchy-wallpaper-theme` on `PATH` + `matugen` — “🎨 Theme from wallpaper” rows in **Theme**: a Material You theme `dynamic` built from the current wallpaper ([script](https://github.com/KamradSmeshnyavy/dotfiles/blob/main/omarchy-themes/scripts/omarchy-wallpaper-theme))

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

## Language

English and Russian. The language comes from `"lang"` in `~/.config/omarchy/customizer.json`, otherwise
from `$LANG` (`ru*` → Russian). Translations live in `i18n/<lang>.json`: the English string is the key —
a new language is one more file.

## License

GPL-3.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). The animation presets come from
[HyDE](https://github.com/HyDE-Project/HyDE), [ML4W](https://github.com/mylinuxforwork/dotfiles),
[end-4](https://github.com/end-4/dots-hyprland) and [NIHIL](https://github.com/poligle/Nihil-Shell)
([credits](animations/CREDITS.md)); Dotify, Glyph lighting and NIHIL sound packs are ported from
[NIHIL](https://github.com/poligle/Nihil-Shell) (MIT, Pol Iglesias); the overlay follows the
style of [Omarchy](https://github.com/basecamp/omarchy)'s own shell plugins (MIT).

Part of [my dotfiles](https://github.com/KamradSmeshnyavy/dotfiles).
