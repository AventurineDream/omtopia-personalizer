# Changelog

## [Unreleased]

### Changed

- Identify this fork as Omtopia Personalizer while retaining the upstream plugin ID for compatibility.
- Keep the customizer open after applying a change: the list and Home status refresh, and queued applies run in order. Applies that open a dialog, terminal, lock preview, launcher or picker still close it first.

### Fixed

- Keep Wallpaper FX random selection away from one-off actions such as model installation.
- Format the Home-page date using the Customizer's selected language.
