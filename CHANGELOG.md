# Changelog

## [Unreleased]

### Changed

- Identify this fork as Omtopia Personalizer while retaining the upstream plugin ID for compatibility.
- Keep the customizer open after applying a change: the list and Home status refresh, applies run one at a time in the order they were asked for, and the footer shows "Applying…" while one runs. Applies that open a dialog, terminal, lock preview, launcher or picker, or that change which shell plugins are loaded, still close it first; the apply itself still runs after the close. Tweaks and typed values wait behind a running apply, so they never overlap it.

### Fixed

- Keep Wallpaper FX random selection away from one-off actions such as model installation.
- Format the Home-page date using the Customizer's selected language.
- Bar Widgets: «Add to bar» works again. ⏎ and the button sent the wrong key for widget rows (the Customizer.qml regex matched `wset:` rows only), so an absent widget was never added.
- Bar Widgets: ⏎ on an on-bar row now removes the widget, as the row text says; it used to move the widget one slot later. «Remove» and ⏎ remove every copy of the id from the layout (bar, tray drawer, un-anchored centre sections) and re-adding puts it back in its old slot.
- Bar Widgets: a widget in the tray drawer is listed under «In the tray drawer», and «Add to bar» moves its existing entry (settings kept) to the end of the right section. Before, it was listed under «Not on the bar» and adding it appended a second entry for the same id. The stock shell draws the drawer, so the widget showed twice there. kamradsmeshnyavy.bar does not draw the tray section: widgets left in the drawer were never visible on that bar, and moving them out of it is what makes them appear.
