# Changelog

## [Unreleased]

### Changed

- Identify this fork as Omtopia Personalizer while retaining the upstream plugin ID for compatibility.
- Keep the customizer open after applying a change: the list and Home status refresh, applies and tweaks run one at a time, in the order they were asked for, and the footer shows "Applying…" while one runs. Applies that open a dialog, terminal, lock preview, launcher or picker, or that change which shell plugins are loaded, still close it first; the apply itself still runs after the close. Tweaks and typed values wait behind a running apply, so they never overlap it.

### Fixed

- Widgets: the 24-hour clock row now changes the widgets config instead of the lock screen's `lock-design.json`. The key `clock24` is declared in both Lock Tweaks and Widgets; a key declared in more than one table is now listed and searched as `TABLE:key` (only from its second table on), and `customizer.sh tweak` resolves that form to its own table. The bare `clock24` still means the Lock Tweaks setting.
- Clicking a category tab moves keyboard focus to its list, so j/k move within the list instead of the rail.
- Theme Switcher preview shows a hint to run "⚡ Cache thumbnails" instead of an empty dark card when no thumbnails are cached yet.
- `install.sh` adds this fork (`AventurineDream/omtopia-personalizer`) rather than the upstream `KamradSmeshnyavy/omarchy-customizer`.
- `install.sh` prints its usage and exits 2 on an unknown flag, a missing `--with` list or an unknown companion, instead of stopping at one line.
- Without a terminal to ask on, `install.sh` says it installs the Customizer alone, instead of printing `/dev/tty` errors and skipping the companions silently.
- `install.sh --with` no longer expands a `*` in the list against the files of the current directory (it is rejected as an unknown companion), and accepts blanks around names such as `bar, lock`.
- The README's Uninstall section lists the config and state paths the Customizer writes: the Omarchy shell files it changes, `~/.config/owe/config.toml`, the reading-mode and window-geometry state, the thumbnail cache and the SDDM themes it downloads.
- The README no longer lists `matugen` for the «🎨 Theme from wallpaper» rows: they need only `omarchy-wallpaper-theme` on `PATH` (the script runs `omarchy-rice-dynamic` and does not call matugen). The row text and the failure message no longer name matugen.
- Offer every style the companion plugins accept in the Clock, OSD, Notification cards and Dashboard style rows; the rows listed only some of them, so the rest could not be picked.
- The Clock, OSD, Notification cards and Dashboard style rows now list the style values the companion plugins branch on or document, so the rest can be picked. Before, the rows listed only some of them.
- Keep Wallpaper FX random selection away from one-off actions such as model installation.
- Format the Home-page date using the Customizer's selected language.
- Bar Widgets: «Add to bar» works again. ⏎ and the button sent the wrong key for widget rows (the Customizer.qml regex matched `wset:` rows only), so an absent widget was never added.
- Bar Widgets: ⏎ on an on-bar row now removes the widget, as the row text says; it used to move the widget one slot later. «Remove» and ⏎ remove every copy of the id from the layout (bar, tray drawer, un-anchored centre sections) and re-adding puts it back in its old slot.
- Bar Widgets: a widget in the tray drawer is listed under «In the tray drawer», and «Add to bar» moves its existing entry (settings kept) to the end of the right section. Before, it was listed under «Not on the bar» and adding it appended a second entry for the same id. The stock shell draws the drawer, so the widget showed twice there. kamradsmeshnyavy.bar does not draw the tray section: widgets left in the drawer were never visible on that bar, and moving them out of it is what makes them appear.
- Translate the seven category titles that stayed English in the Russian UI: Bar Skin, Bar Layout, Bar Tweaks, Lock Tweaks, Recolor, Theme Switcher and Wallpaper FX.
- Translate the Transparency preview's window labels, its opacity/blur chip and the bar mock's media placeholder, which stayed English in the Russian UI.
- Pick up a language change in `customizer.json` the next time the Customizer opens, without restarting the shell (the overlay used to keep the old language for its chrome while list rows were already translated).
- Applying a style keeps your bar widgets: the style's bar position and arrangement apply, but the widgets (and the tray drawer) stay yours, as the README describes. A preset's style part works the same way; a preset's own saved bar layout still applies as saved.
- Restore previous setup brings back a stock bar layout exactly as it was saved, instead of keeping the widgets you have now.
- "In use" follows a restore: a preset with nothing comparable (such as DOT-MATRIX with "Apply theme" off) is no longer reported as in use by list order, and "Restore previous setup" reports the preset that was in use when its snapshot was taken, or `custom`.
- "In use" follows a restore: a preset that compares nothing (such as DOT-MATRIX with "Apply theme" off) is no longer shown as in use after a restore, and "Restore previous setup" restores the preset that was in use when the snapshot was taken, or `custom`.
- Windows tab shows the value Hyprland really uses when a key is not in windows.json (after «x» or «Reset window geometry»), read from the Hyprland Lua config chain, instead of the settings.json placeholder (gaps 2/4, rounding 10, …).
- Transparency shows no preset in use on a fresh system instead of "subtle"; the Home card and list no longer mark a preset the compositor is not using.
- Windows tab shows the value Hyprland uses when a key is not in windows.json (after «x» or «Reset window geometry»), read with `hyprctl -j getoption`, instead of the settings.json placeholder (gaps 2/4, rounding 10, …). A key the file sets shows "default: Hyprland config" and is marked as changed against the live value. A CSS gap whose sides differ (e.g. "5 10") falls back to the settings.json default.
- «Reset window geometry» also turns the no-gaps toggle off, so the No gaps row and the gaps rows agree.
- Windows tab shows the value Hyprland uses when a key is not in windows.json (after «x» or «Reset window geometry»), read with `hyprctl -j getoption`, instead of the settings.json placeholder (gaps 2/4, rounding 10, …). A key the file sets shows "default: Hyprland config" and is always marked, since the user set it. A CSS gap whose sides differ (e.g. "5 10") falls back to the settings.json default.
- A hung `hyprctl` costs one second per list, not one per row; the bash mirror of the list does the same.
- «Reset window geometry» leaves the no-gaps toggle as it is, so the No gaps row and the gap rows show the same state.
- Transparency shows no preset in use on a fresh system instead of "subtle"; the Home card and list no longer mark a preset the compositor is not using. On a fresh system the first next/prev applies "subtle"; styles that name an opacity report "custom" there.
- Presets saved on a fresh system no longer store an empty opacity; `opacity.sh restore` with a saved name that no longer exists keeps the live values instead of exiting 1.
- Theme Switcher rows whose value equals the sentinel (0 / -1, "from the style / theme") show the default's words, not a bare number or a stray change mark.
- Dock pinned rows resolve app names from desktop files in $XDG_DATA_HOME and $XDG_DATA_DIRS, not only the fixed directories.
- Bar Widgets no longer lists the Tray collapse and monochrome settings: no installed plugin provides them, so they never took effect.
- Unexpected errors in a Customizer step now show as a toast with the error text; before, the step failed silently.
- DOT-MATRIX style names the current widget ids (`omarchy.tray`, `omarchy.agents`, `omarchy.monitor`, `omarchy.network`, `omarchy.bluetooth`, `omarchy.audio`), so applying it puts the tray and the panels on the bar instead of adding widgets nobody draws.
- Save and delete your own presets, styles, bar skins and bar layouts without zenity: ⏎ on the 💾 row opens the name field in the row, and `D` asks in the footer. Home's "Save preset" opens the same field, and thumbnail clean-up asks in the footer too.
- Without zenity, the actions that need it stop with a "Needs zenity (sudo pacman -S zenity)" notice and keep the Customizer open; colour and text tweaks are typed in place instead.
- ⏎ on the Photos folder row opens the folder picker; it used to reset the folder to the default.
