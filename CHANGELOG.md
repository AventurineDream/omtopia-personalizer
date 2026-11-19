# Changelog

## [Unreleased]

### Changed

- Identify this fork as Omtopia Personalizer while retaining the upstream plugin ID for compatibility.
- Keep the customizer open after applying a change: the list and Home status refresh, applies run one at a time in the order they were asked for, and the footer shows "Applying…" while one runs. Applies that open a dialog, terminal, lock preview, launcher or picker, or that change which shell plugins are loaded, still close it first; the apply itself still runs after the close. Tweaks and typed values wait behind a running apply, so they never overlap it.

### Fixed

- Widgets: the 24-hour clock row now changes the widgets config instead of the lock screen's `lock-design.json`. The key `clock24` is declared in both Lock Tweaks and Widgets; a key declared in more than one table is now listed and searched as `TABLE:key` (only from its second table on), and `customizer.sh tweak` resolves that form to its own table. The bare `clock24` still means the Lock Tweaks setting.
- Clicking a category tab moves keyboard focus to its list, so j/k move within the list instead of the rail.
- Keep Wallpaper FX random selection away from one-off actions such as model installation.
- Format the Home-page date using the Customizer's selected language.
- Bar Widgets: «Add to bar» works again. ⏎ and the button sent the wrong key for widget rows (the Customizer.qml regex matched `wset:` rows only), so an absent widget was never added.
- Bar Widgets: ⏎ on an on-bar row now removes the widget, as the row text says; it used to move the widget one slot later. «Remove» and ⏎ remove every copy of the id from the layout (bar, tray drawer, un-anchored centre sections) and re-adding puts it back in its old slot.
- Bar Widgets: a widget in the tray drawer is listed under «In the tray drawer», and «Add to bar» moves its existing entry (settings kept) to the end of the right section. Before, it was listed under «Not on the bar» and adding it appended a second entry for the same id. The stock shell draws the drawer, so the widget showed twice there. kamradsmeshnyavy.bar does not draw the tray section: widgets left in the drawer were never visible on that bar, and moving them out of it is what makes them appear.
- Translate the seven category titles that stayed English in the Russian UI: Bar Skin, Bar Layout, Bar Tweaks, Lock Tweaks, Recolor, Theme Switcher and Wallpaper FX.
- Pick up a language change in `customizer.json` the next time the Customizer opens, without restarting the shell (the overlay used to keep the old language for its chrome while list rows were already translated).
- Applying a style keeps your bar widgets: the style's bar position and arrangement apply, but the widgets (and the tray drawer) stay yours, as the README describes. A preset's style part works the same way; a preset's own saved bar layout still applies as saved.
- Restore previous setup brings back a stock bar layout exactly as it was saved, instead of keeping the widgets you have now.
- "In use" follows a restore: a preset with nothing comparable (such as DOT-MATRIX with "Apply theme" off) is no longer reported as in use by list order, and "Restore previous setup" reports the preset that was in use when its snapshot was taken, or `custom`.
- "In use" follows a restore: a preset that compares nothing (such as DOT-MATRIX with "Apply theme" off) is no longer shown as in use after a restore, and "Restore previous setup" restores the preset that was in use when the snapshot was taken, or `custom`.
