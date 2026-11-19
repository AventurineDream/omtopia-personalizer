// @file Wiring test for the Customizer's preview card after a live preview is undone.
//
// Bug: on a Bar Skin list, `h` restores the live bar-skin.json (revertPreview) but the card (bar mock and
// row text) kept showing the hovered skin, because previewText still held that row's file. Customizer.qml
// has no QML runtime in the test suite, so this checks the statements the fix depends on in the source,
// the same way test_random_pick_flow.cjs checks Customizer.qml's wiring. Run: node --test tests/test_bar_skin_card.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PLUGIN = path.join(__dirname, '..');
const qml = fs.readFileSync(path.join(PLUGIN, 'Customizer.qml'), 'utf8');

// Source of one top-level QML function: from its header to the "  }" that closes it at the same indent.
function functionBody(header) {
  const start = qml.indexOf(header);
  assert.notEqual(start, -1, `${header.trim()} exists in Customizer.qml`);
  const end = qml.indexOf('\n  }\n', start);
  assert.notEqual(end, -1, `${header.trim()} closes at its own indent`);
  return qml.slice(start, end);
}

test('revertPreview clears the card text of a live category before its early return', () => {
  const body = functionBody('  function revertPreview() {');
  const clear = body.indexOf('if (root.category.live) root.previewText = ""');
  const early = body.indexOf('if (!key) return');
  assert.notEqual(clear, -1, 'the card text is cleared for live categories');
  assert.ok(clear < early, 'the clear runs even when no preview was started (a key pressed before previewTimer fired)');
  assert.ok(body.includes('-restore'), 'the restore command still runs for an active preview');
});

test('selectionChanged re-reads the row file even when its path is unchanged', () => {
  const body = functionBody('  function selectionChanged() {');
  const set = body.indexOf('previewFile.path = previewPath');
  const reload = body.indexOf('if (previewPath) previewFile.reload()');
  assert.notEqual(set, -1, 'previewFile follows the selected row');
  assert.ok(reload > set, 'the reload comes after the path assignment, so re-selecting the same row brings the text back');
});

test('the bar mock falls back to the live skin and bar when no preview text is set', () => {
  assert.ok(functionBody('  function mockSkin() {').includes('return root.activeSkin'),
    'mockSkin falls back to activeSkin');
  assert.ok(functionBody('  function mockBar() {').includes('return root.activeBar'),
    'mockBar falls back to activeBar');
});
