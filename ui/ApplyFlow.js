/** @file Stay-open decision for applies: which `customizer.sh apply <category> <value>` calls keep
 * the overlay open.
 *
 * An apply that opens a surface the user has to answer or see (a zenity dialog, a terminal, a lock
 * preview, the launcher, a picker) or changes which shell plugins are loaded closes the overlay
 * first, as it always did. Every apply the table classifies as open keeps the overlay open and the
 * overlay refreshes its list; anything the table does not classify closes it.
 *
 * needsZenity lists the applies that open a zenity dialog or list; without zenity the overlay refuses them
 * and says why, instead of closing.
 *
 * Shared between Customizer.qml and tests/test_apply_flow.cjs. Pure functions only: nothing here
 * spawns a process. tests/apply_surface_probe.py checks this table against the apply_ops.apply()
 * branches, so a branch that opens a surface cannot be listed as open here unnoticed.
 */
.pragma library
.import "RandomCandidates.js" as RandomCandidates

/** One-off Wallpaper FX actions that keep the overlay open: owe-toggle (pause or resume the live
 * wallpaper), outline-warm (queues cut-outs in the background), outline-status (no effect).
 * outline-install (opens a terminal) and enable-plugin (changes the loaded plugins) are not listed.
 */
var FX_OPEN_ACTIONS = ["owe-toggle", "outline-warm", "outline-status"]

/** Per-category stay-open rules, keyed by the category key Customizer.qml passes to run().
 *
 * Each entry names the apply_ops.apply() branch it maps to. Fields, all optional:
 *   only / onlyPrefix  allowlist: the value must be listed or start with a prefix; every other value closes.
 *   close / closePrefix  denylist: a listed value or a prefix match closes; every other value keeps the overlay open.
 *   transition  wallpaper-fx only: a transition value (isTransition) keeps the overlay open.
 * A category with no entry closes for every value (bar-widgets has no apply_ops branch).
 */
var RULES = {
  // presets → apply(): "save" → save_user_preset (bare: zenity asks for a name; the overlay's name prompt
  // passes --name and never gets here); "tweak:" → tweak_pick,
  // which can open a zenity color or text picker; a preset path → apply_preset; geometry-reset → geometry_reset.
  presets: { close: ["save"], closePrefix: ["tweak:"] },
  // fonts → omarchy-font-profile <value>, no UI.
  fonts: {},
  // sounds → pack: sets soundPack; test: plays a sound; tweak: → tweak_pick (may open a zenity picker).
  sounds: { closePrefix: ["tweak:"] },
  // styles → save → save_user_style (bare: zenity asks for a name; in-window saves pass --name); tweak: → tweak_pick; a style path → apply_style.
  styles: { close: ["save"], closePrefix: ["tweak:"] },
  // themes → dynamic: runs omarchy-wallpaper-theme (matugen); any other value → omarchy theme set.
  // Theme, preset and style applies keep the overlay open on purpose: they run omarchy-theme-set,
  // which may play its background intro beneath the overlay (omarchy-theme-set prepares an intro
  // unless ~/.local/state/omarchy/toggles/background-intros-off exists, then waits for it). The overlay
  // stays up as the user asked for, and the intro is accepted as a visible effect under it.
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
  // bar-layouts → save → save_user_layout (bare: zenity; in-window saves pass --name); a layout file → shell_apply_layout.
  "bar-layouts": { close: ["save"] },
  // bar-skins → save → save_user_skin (bare: zenity; in-window saves pass --name); a skin file → bar_skin_preview.
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
  // theme-switcher → prune → zenity question when bare (the overlay asks in its footer and passes --yes); cache → picker_cache (no UI); style: → sets the picker style; tweak: → tweak_pick.
  "theme-switcher": { close: ["prune"], closePrefix: ["tweak:"] },
  // lock → sddm-login-glyph / sddm-login / sddm-fetch-all open a terminal; sddm-fetch → zenity list;
  // regen-thumbs / missing-thumbs show the lock preview over the screen; any other value is a lock design.
  // sddm-login opens a terminal only when the current lock is an sddm theme; it closes regardless.
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

/** Whether `value` sets a Wallpaper FX transition, the values that keep the overlay open.
 *
 * RandomCandidates lists only the transitions the random pick may choose. "none" (No animation) is a
 * transition too but is not random-eligible, so it is named here.
 *
 * @param value row value of the wallpaper-fx category, e.g. "fade" or "none".
 * @returns true for a transition value, false for anything else (including actions).
 */
function isTransition(value) {
  return value === "none" || RandomCandidates.WALLPAPER_FX_TRANSITIONS[value] === true
}

/** Whether `value` equals one of `exact` or starts with one of `prefixes`.
 *
 * @param exact array of exact values, or undefined.
 * @param prefixes array of prefixes, or undefined.
 * @param value the row value to test.
 * @returns true on a match; false when neither list matches (or both are undefined).
 */
function matches(exact, prefixes, value) {
  if (exact && exact.indexOf(value) !== -1) return true
  for (var i = 0; prefixes && i < prefixes.length; i++) if (value.indexOf(prefixes[i]) === 0) return true
  return false
}

/** Whether applying `value` in `categoryKey` keeps the overlay open.
 *
 * @param categoryKey customizer.sh category key (Customizer.qml category.key), e.g. "anims".
 * @param value the row value passed to `customizer.sh apply`; empty, null or undefined → false.
 * @returns true when the apply opens no surface the user must answer or see, so the overlay can stay
 *   open while it runs; false when the overlay must close first, or the apply is not classified.
 */
function keepsOpen(categoryKey, value) {
  var rule = Object.prototype.hasOwnProperty.call(RULES, categoryKey) ? RULES[categoryKey] : null
  var v = value === undefined || value === null ? "" : String(value)
  if (rule === null || v === "") return false
  if (rule.transition && isTransition(v)) return true
  if (rule.only !== undefined) return matches(rule.only, rule.onlyPrefix, v)
  return !matches(rule.close, rule.closePrefix, v)
}

/** The CLI forms that open a zenity dialog or list, by category key: a bare `customizer.sh apply <category> <value>`
 * opens one. The overlay's in-window forms (save with --name, prune with --yes, the *-delete commands) never reach
 * run(), so they are not listed. The overlay does not reach a bare prune either (activate() asks in the footer), but
 * the prune entry stays for the CLI form. Colour, text, file and folder tweak rows are not listed either: their picker
 * depends on the row's kind, and Customizer.qml checks that itself.
 */
var ZENITY_APPLIES = {
  presets: ["save"],
  styles: ["save"],
  "bar-skins": ["save"],
  "bar-layouts": ["save"],
  walls: ["pick-dir", "pick-files"],
  dotify: ["pick-dir", "pick-files"],
  dock: ["pin-pick"],
  lock: ["sddm-fetch"],
  "theme-switcher": ["prune"],
}

/** Whether applying `value` in `categoryKey` needs zenity: the bare apply opens a dialog or list.
 *
 * @param categoryKey customizer.sh category key, e.g. "walls".
 * @param value the row value passed to `customizer.sh apply`.
 * @returns true for a value listed in ZENITY_APPLIES, false for anything else.
 */
function needsZenity(categoryKey, value) {
  var list = Object.prototype.hasOwnProperty.call(ZENITY_APPLIES, categoryKey) ? ZENITY_APPLIES[categoryKey] : null
  return list !== null && list.indexOf(String(value)) !== -1
}
