// @file Tests for the preview-card text that survives an undo (ui/PreviewCard.js, used by revertPreview()).
//
// Bar Skin: the card draws the hovered skin file, so `h` must drop it and the mock falls back to the live
// skin. Animations: the same previewText is the curve source for AnimsPreview and must survive the undo.
// Other categories keep their text. The helper runs here exactly as Customizer.qml runs it: nothing
// spawns a process. Run: node --test tests/test_bar_skin_card.cjs
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
