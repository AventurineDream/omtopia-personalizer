# Changelog

## [Unreleased]

### Changed

- Identify this fork as Omtopia Personalizer while retaining the upstream plugin ID for compatibility.
- Keep the customizer open after applying a change: the list and Home status refresh, applies run one at a time in the order they were asked for, and the footer shows "Applying…" while one runs. Applies that open a dialog, terminal, lock preview, launcher or picker, or that change which shell plugins are loaded, still close it first; the apply itself still runs after the close. Tweaks and typed values wait behind a running apply, so they never overlap it.

### Fixed

- Keep Wallpaper FX random selection away from one-off actions such as model installation.
- Format the Home-page date using the Customizer's selected language.
