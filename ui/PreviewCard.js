/** @file Preview-card text after a live preview is undone (`h` / leaving the category).
 *
 * The card reads previewText, the file of the row under the cursor. Shared between Customizer.qml and
 * tests/test_bar_skin_card.cjs, so the test runs the same decision the shell runs. Pure functions only:
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
