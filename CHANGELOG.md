# Changelog

## [Unreleased]

### Changed

- Identify this fork as Omtopia Personalizer while retaining the upstream plugin ID for compatibility.

### Fixed

- Keep Wallpaper FX random selection away from one-off actions such as model installation.
- Format the Home-page date using the Customizer's selected language.
- Bar Widgets: «Add to bar» works again — ⏎ and the button sent the wrong key for widget rows (the regex in Customizer.qml matched `wset:` only), so adding a widget and removing one did nothing.
- Bar Widgets: a widget in the tray drawer is listed under «In the tray drawer» and «Add to bar» moves its existing entry (settings kept) onto the bar, instead of adding a second entry for the same id that the bar drew twice.
