/** @file In-window save and delete for the user's own items (presets, styles, bar skins, bar layouts):
 * which categories have a 💾 save row and the name a new save starts with, the backend command that
 * moves one of the user's items to the trash, and the refusal for any other row. It also holds the small
 * decisions the overlay makes around them: which handler takes a key (keyRoute), what a save result means
 * (saveOutcome), what a tab switch drops (clearTransient) and which queued write runs next (nextLane).
 *
 * Shared between Customizer.qml and tests/test_in_window.cjs. The commands these names feed carry
 * --name or --yes (see backend/customizer/apply_ops.py and preview_ops.py), so neither opens a zenity
 * dialog. Pure functions only: nothing here spawns a process.
 */
.pragma library

/** Per category key with own items: the name a new save starts with, the backend command that moves one
 * of the user's items to the trash (called as `<command> <path> --yes`), and the refusal for any other row.
 * The refusal texts are the backend's own (preview_ops.py), so the footer reads the same either way.
 */
var OWN_ITEMS = {
  presets: { defaultName: "My Preset", remove: "preset-delete", refusal: "Only your own presets (★) can be deleted" },
  styles: { defaultName: "My Style", remove: "style-delete", refusal: "Only your own styles (★) can be deleted" },
  "bar-skins": { defaultName: "my-skin", remove: "skin-delete", refusal: "Only your own skins (★) can be deleted" },
  "bar-layouts": { defaultName: "my-layout", remove: "layout-delete", refusal: "Only your own layouts (★) can be deleted" },
}

/** Whether a category has own items: a 💾 save row and deletable ★ rows.
 *
 * @param categoryKey customizer.sh category key, e.g. "presets".
 * @returns true for presets, styles, bar-skins and bar-layouts; false for every other key.
 */
function has(categoryKey) {
  return Object.prototype.hasOwnProperty.call(OWN_ITEMS, categoryKey)
}

/** Whether a row is the 💾 save row: ⏎ opens the name prompt instead of applying the row.
 *
 * @param categoryKey customizer.sh category key.
 * @param value the row value, e.g. "save".
 * @returns true for the "save" row of a category with own items.
 */
function isSaveRow(categoryKey, value) {
  return has(categoryKey) && value === "save"
}

/** The name a new save starts with: the text the name prompt opens with.
 *
 * @param categoryKey customizer.sh category key.
 * @returns the default name, or "" for a category without own items.
 */
function defaultSaveName(categoryKey) {
  return has(categoryKey) ? OWN_ITEMS[categoryKey].defaultName : ""
}

/** The backend command that moves one of the user's items to the trash.
 *
 * @param categoryKey customizer.sh category key.
 * @returns the command name; "" for a category without own items.
 */
function removeCommand(categoryKey) {
  return has(categoryKey) ? OWN_ITEMS[categoryKey].remove : ""
}

/** The reason shown when D is pressed on a row that is not one of the user's own items.
 *
 * @param categoryKey customizer.sh category key.
 * @returns the message (a key of i18n/ru.json); "" for a category without own items.
 */
function refusal(categoryKey) {
  return has(categoryKey) ? OWN_ITEMS[categoryKey].refusal : ""
}

/** Clears the footer question and the notice of the overlay. A question's yes-callback reads the overlay's
 * state when it is answered, so every change of tab or view clears them first.
 *
 * @param o the overlay object (Customizer.qml passes root); its confirm and notice are set in place.
 */
function clearTransient(o) {
  o.confirm = null
  o.notice = ""
}

/** What a finished in-window save means, by its exit code. The backend exits 3 (EXISTS) for a taken name
 * without --overwrite, so the overlay asks to overwrite instead of reporting a failure.
 *
 * @param code exit code of `customizer.sh apply <category> save --name <name>`.
 * @returns "saved" for 0, "taken" for 3, "failed" for any other code.
 */
function saveOutcome(code) {
  if (code === 0) return "saved"
  if (code === 3) return "taken"
  return "failed"
}

/** Which handler takes a key press: a footer question first (⏎ or y answers it, any other key cancels), then an
 * open name or value field (the key belongs to the field), then the overlay's own commands.
 *
 * @param editing whether a field is open in the rows of the current tab.
 * @param confirm whether a footer question waits for its answer.
 * @returns "confirm", "field" or "overlay".
 */
function keyRoute(editing, confirm) {
  if (confirm) return "confirm"
  if (editing) return "field"
  return "overlay"
}

/** Which queued write starts next. Applies, tweak steps and a value waiting in pendingSet share one order, the order
 * they were asked for, by sequence number: a save waits for the values asked before it, and values asked after it
 * wait for the save.
 *
 * @param applySeq sequence number of the first queued apply, or -1 when none is queued.
 * @param tweakSeq sequence number of the first queued tweak step, or -1 when none is queued.
 * @param pendingSeq sequence number of the value waiting in pendingSet, or -1 when none waits.
 * @returns "apply", "tweak" or "pending" for the write asked first, "none" when all three are empty.
 */
function nextLane(applySeq, tweakSeq, pendingSeq) {
  var lane = "none"
  var seq = -1
  var lanes = [["apply", applySeq], ["tweak", tweakSeq], ["pending", pendingSeq]]
  for (var i = 0; i < lanes.length; i++) {
    var s = lanes[i][1]
    if (s >= 0 && (seq < 0 || s < seq)) { lane = lanes[i][0]; seq = s }
  }
  return lane
}
