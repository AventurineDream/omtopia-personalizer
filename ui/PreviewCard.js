/** @file Preview-card text after a live preview is undone (`h` / leaving the category), and the decisions
 * that bring it back when the row is selected again.
 *
 * The card reads previewText, the file of the row under the cursor. Shared between Customizer.qml and
 * tests/test_bar_skin_card.cjs, so the test runs the same decisions the shell runs. Pure functions only:
 * nothing here spawns a process or touches config state.
 */
.pragma library

/** Card text that remains once revertPreview() has restored the live state.
 *
 * Bar Skin only. Its card (bar mock and skin text) draws the hovered skin file; after the undo that skin
 * is no longer applied, so the text is dropped and the mock falls back to the live skin.
 * Animations also keep their text, because AnimsPreview draws the hovered row's curves from it. Dropping
 * it there left the scene on default curves and the note. Every other category keeps its text as it was.
 *
 * @param {string} categoryKey  Customizer category key, e.g. "bar-skins" or "anims".
 * @param {string} currentText  previewText before the undo ("" when no row file is loaded).
 * @returns {string} "" for bar-skins, otherwise currentText unchanged.
 */
function revertPreviewText(categoryKey, currentText) {
  return categoryKey === "bar-skins" ? "" : currentText
}

/** Whether a click on row `index` must run selectionChanged().
 *
 * Re-entering the list from the category rail (pane 0, after `h`) must run it even on the row that is
 * already highlighted: that restarts the live preview and re-reads the row file that revertPreview()
 * cleared. A click on the highlighted row while the list is open changes nothing.
 *
 * @param {number} pane          0 = category rail, 1 = row list, before the click.
 * @param {number} selectedIndex row highlighted before the click.
 * @param {number} index         row clicked.
 * @returns {boolean} true when selectionChanged() must run.
 */
function clickNeedsRefresh(pane, selectedIndex, index) {
  return pane !== 1 || selectedIndex !== index
}

/** Whether selectionChanged() must call FileView.reload() on the row file.
 *
 * A FileView does not reload for an unchanged path. The card text is cleared by revertPreview() for Bar
 * Skin, so the file is read again when that row is selected again. A changed path loads by itself, and a
 * file edited on disk reloads through watchChanges.
 *
 * @param {boolean} samePath     the row file path equals the path already set on the FileView.
 * @param {string} previewPath   path of the selected row ("" when no row file applies).
 * @param {string} previewText   card text as it stands.
 * @returns {boolean} true when the file must be read again.
 */
function shouldReloadPreview(samePath, previewPath, previewText) {
  return samePath && previewPath !== "" && previewText === ""
}
