/** @file In-window save and delete for the user's own items (presets, styles, bar skins, bar layouts):
 * which categories have a 💾 save row and the name a new save starts with, the backend command that
 * moves one of the user's items to the trash, and the refusal for a row that is not the user's.
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
