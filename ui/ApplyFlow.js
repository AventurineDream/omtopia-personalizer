/** @file Stay-open decision for applies: which `customizer.sh apply <category> <value>` calls keep
 * the overlay open.
 *
 * An apply that opens a surface the user has to answer or see (a zenity dialog, a terminal, a
 * lock preview, the launcher, the picker) or changes which shell plugins are loaded closes the
 * overlay, as it always did. Every other apply keeps it open and the overlay refreshes its list.
 *
 * Shared between Customizer.qml and tests/test_apply_flow.cjs. Pure functions only: nothing here
 * spawns a process. A value this table does not classify closes the overlay (fail toward closing).
 */
.pragma library
.import "RandomCandidates.js" as RandomCandidates

// Wallpaper FX one-off actions that keep the overlay open: owe-toggle (owe pause/resume),
// outline-warm (queues cut-outs in the background), outline-status (no effect).
// outline-install (opens a terminal) and enable-plugin (changes the loaded plugins) are left out.
var FX_OPEN_ACTIONS = ["owe-toggle", "outline-warm", "outline-status"]

// Per category: the rule for apply_ops.apply(category, value). Each entry names the apply_ops
// branch it maps to; the rule decides what happens to the values in that branch.
//   only / onlyPrefix  allowlist: the value must be listed or start with a prefix; all else closes.
//   close / closePrefix  denylist: listed values close; every other value keeps the overlay open.
//   transition  wallpaper-fx only: a transition value (isTransition) also keeps the overlay open.
// A category missing here closes for every value (bar-widgets has no apply_ops branch).
var RULES = {
  // presets → apply(): "save" → save_user_preset (zenity entry and question); "tweak:" → tweak_pick,
  // which can open a zenity color or text picker; a preset path → apply_preset; geometry-reset → geometry_reset.
  presets: { close: ["save"], closePrefix: ["tweak:"] },
  // fonts → omarchy-font-profile <value>, no UI.
  fonts: {},
  // sounds → pack: sets soundPack; test: plays a sound; tweak: → tweak_pick (may open a zenity picker).
  sounds: { closePrefix: ["tweak:"] },
  // styles → save → save_user_style (zenity); tweak: → tweak_pick; a style path → apply_style.
  styles: { close: ["save"], closePrefix: ["tweak:"] },
  // themes → dynamic: runs omarchy-wallpaper-theme (matugen); any other value → omarchy theme set.
  themes: {},
  // theme-walls → omarchy theme bg set <path>.
  "theme-walls": {},
  // walls → pick-dir / pick-files → _pick_dir / _pick_images (zenity); a file → recolor (lutgen, no UI).
  walls: { close: ["pick-dir", "pick-files"] },
  // dotify → pick-dir / pick-files → zenity; current, arch, a file → dotify; tweak: → tweak_pick.
  dotify: { close: ["pick-dir", "pick-files"], closePrefix: ["tweak:"] },
  // glyph → test:* → omarchy-shell glyph (no UI); tweak: → tweak_pick (may open a zenity color picker).
  glyph: { closePrefix: ["tweak:"] },
  // launcher → open → preview_ops.launcher_open (shows the launcher); skin: → sets the launcher skin; tweak: → tweak_pick.
  launcher: { close: ["open"], closePrefix: ["tweak:"] },
  // anims → copies the animation file and runs hyprctl reload.
  anims: {},
  // bar-layouts → save → save_user_layout (zenity); a layout file → shell_apply_layout.
  "bar-layouts": { close: ["save"] },
  // bar-skins → save → save_user_skin (zenity); a skin file → bar_skin_preview.
  "bar-skins": { close: ["save"] },
  // bar-tweaks / lock-tweaks / widgets / dashboard / osd / notifications → every value is tweak_pick,
  // which may open a zenity color, text, folder or file picker, so none of them keep the overlay open.
  "bar-tweaks": { only: [] },
  "lock-tweaks": { only: [] },
  widgets: { only: [] },
  dashboard: { only: [] },
  osd: { only: [] },
  notifications: { only: [] },
  // wallpaper-fx → a transition value sets the transition; one-off actions per FX_OPEN_ACTIONS;
  // tweak: and every other action (outline-install, enable-plugin, unknown names) close.
  "wallpaper-fx": { only: FX_OPEN_ACTIONS, transition: true },
  // theme-switcher → prune → zenity question; cache → picker_cache (no UI); style: → sets the picker style; tweak: → tweak_pick.
  "theme-switcher": { close: ["prune"], closePrefix: ["tweak:"] },
  // lock → sddm-login-glyph / sddm-login / sddm-fetch-all open a terminal; sddm-fetch → zenity list;
  // regen-thumbs / missing-thumbs show the lock preview over the screen; any other value is a lock design.
  lock: {
    close: ["sddm-login-glyph", "sddm-login", "sddm-fetch-all", "sddm-fetch", "regen-thumbs", "missing-thumbs"],
  },
  // dock → pos: / unpin: / autohide run omarchy dock; toggle enables or disables the omarchy.dock plugin
  // and pin-pick opens a zenity list, so both close.
  dock: { only: ["autohide"], onlyPrefix: ["pos:", "unpin:"] },
  // shaders → reading runs reading-mode.sh; toggle / next / a shader name → crt-toggle.sh; tweak: → tweak_pick.
  shaders: { closePrefix: ["tweak:"] },
  // opacity → opacity.sh set <preset>.
  opacity: {},
  // blur → blur.sh set <preset>.
  blur: {},
  // windows → geometry-reset → geometry_reset; tweak: → tweak_pick (may open a zenity color picker).
  windows: { only: ["geometry-reset"] },
}

// True when a value sets a Wallpaper FX transition. RandomCandidates lists only the transitions
// the random pick may choose; "none" (No animation) is a transition too, but it is excluded from
// random picks, so it is named here.
function isTransition(value) {
  return value === "none" || RandomCandidates.WALLPAPER_FX_TRANSITIONS[value] === true
}

// True when the value matches one of the exact names or starts with one of the prefixes.
function matches(exact, prefixes, value) {
  if (exact && exact.indexOf(value) !== -1) return true
  for (var i = 0; prefixes && i < prefixes.length; i++) if (value.indexOf(prefixes[i]) === 0) return true
  return false
}

/** Whether applying `value` in `categoryKey` keeps the overlay open.
 *
 * @param categoryKey customizer.sh category key (Customizer.qml category.key), e.g. "anims".
 * @param value the row value passed to `customizer.sh apply`; empty or unknown → false.
 * @returns true when the apply opens no surface the user must answer or see, so the overlay can stay
 *   open while it runs; false when the overlay must close first (or the apply is unclassified).
 */
function keepsOpen(categoryKey, value) {
  var rule = Object.prototype.hasOwnProperty.call(RULES, categoryKey) ? RULES[categoryKey] : null
  var v = value === undefined || value === null ? "" : String(value)
  if (rule === null || v === "") return false
  if (rule.transition && isTransition(v)) return true
  if (rule.only !== undefined) return matches(rule.only, rule.onlyPrefix, v)
  return !matches(rule.close, rule.closePrefix, v)
}
