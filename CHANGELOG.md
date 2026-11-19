# Changelog

## [Unreleased]

### Changed

- Identify this fork as Omtopia Personalizer while retaining the upstream plugin ID for compatibility.
- Keep the customizer open after applying a change: the list and Home status refresh, applies and tweaks run one at a time, in the order they were asked for, and the footer shows "Applying…" while one runs. Applies that open a dialog, terminal, lock preview, launcher or picker, or that change which shell plugins are loaded, still close it first; the apply itself still runs after the close. Tweaks and typed values wait behind a running apply, so they never overlap it.

### Fixed

- Keep Wallpaper FX random selection away from one-off actions such as model installation.
- Format the Home-page date using the Customizer's selected language.
- Save and delete your own presets, styles, bar skins and bar layouts without zenity: ⏎ on the 💾 row opens the name field in the row, and `D` asks in the footer. Home's "Save preset" opens the same field, and thumbnail clean-up asks in the footer too.
- Without zenity, the actions that need it stop with a "Needs zenity (sudo pacman -S zenity)" notice and keep the Customizer open; colour and text tweaks are typed in place instead.
