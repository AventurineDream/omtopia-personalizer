// @file Tests for the preview-card decisions in ui/PreviewCard.js, the same functions Customizer.qml calls.
//
// Bar Skin: the card draws the hovered skin file, so `h` must drop it and the mock falls back to the live
// skin. Animations: the same previewText is the curve source for AnimsPreview and must survive the undo.
// Re-entry: clicking the row that was highlighted before `h` must refresh the list, and the row file must
// be read again once its card text was cleared. Nothing here spawns a process.
// Run: node --test tests/test_bar_skin_card.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const PLUGIN = path.join(__dirname, '..');
const sourcePath = path.join(PLUGIN, 'ui/PreviewCard.js');
const source = fs.readFileSync(sourcePath, 'utf8').replace(/^\.pragma library\s*$/m, '');
const card = {};
vm.runInNewContext(source, card, { filename: sourcePath });

const SKIN_TEXT = '{\n  "form": "underline"\n}';
const LUA_TEXT = 'animations { curve = "easeOut" }';
const SKIN_PATH = '/home/u/.config/omarchy/themes/bar-skins/underline.json';
const RAIL = 0;
const LIST = 1;

test('Bar Skin: undoing the preview drops the hovered skin text', () => {
  assert.equal(card.revertPreviewText('bar-skins', SKIN_TEXT), '');
});

test('Bar Skin: an already-empty card stays empty', () => {
  assert.equal(card.revertPreviewText('bar-skins', ''), '');
});

test('Animations: the live preview curves survive the undo', () => {
  // Clearing this text left AnimsPreview on default curves and the note after `h`.
  assert.equal(card.revertPreviewText('anims', LUA_TEXT), LUA_TEXT);
});

test('other categories keep their card text unchanged', () => {
  for (const key of ['opacity', 'blur', 'bar-layouts', 'bar-tweaks', 'presets', 'styles', 'themes']) {
    assert.equal(card.revertPreviewText(key, SKIN_TEXT), SKIN_TEXT, key);
    assert.equal(card.revertPreviewText(key, ''), '', key);
  }
});

test('re-entry: a click from the rail on the row highlighted before h refreshes the list', () => {
  // The P2 path: after h the row stays highlighted and pane is RAIL. The old clickSelect returned early
  // for this row, so selectionChanged never ran and the cleared card stayed blank.
  assert.equal(card.clickNeedsRefresh(RAIL, 3, 3), true);
  assert.equal(card.clickNeedsRefresh(RAIL, 0, 3), true);
});

test('re-entry: a click on the highlighted row while the list is open changes nothing', () => {
  assert.equal(card.clickNeedsRefresh(LIST, 3, 3), false);
});

test('re-entry: a click on another row always refreshes', () => {
  assert.equal(card.clickNeedsRefresh(LIST, 3, 4), true);
  assert.equal(card.clickNeedsRefresh(RAIL, 3, 4), true);
});

test('re-reading: the cleared card text of the same row is loaded again', () => {
  assert.equal(card.shouldReloadPreview(true, SKIN_PATH, ''), true);
});

test('re-reading: a loaded card text is not read again', () => {
  assert.equal(card.shouldReloadPreview(true, SKIN_PATH, SKIN_TEXT), false);
});

test('re-reading: a changed path loads by itself, so no extra read', () => {
  assert.equal(card.shouldReloadPreview(false, SKIN_PATH, ''), false);
});

test('re-reading: a row without a preview file has nothing to read', () => {
  assert.equal(card.shouldReloadPreview(true, '', ''), false);
});
