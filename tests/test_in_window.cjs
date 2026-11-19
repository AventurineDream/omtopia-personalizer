// @file Tests for the in-window save and delete rules (ui/InWindow.js): which categories have a 💾 save row
// and deletable ★ rows, the name a new save starts with, the delete command and the refusal for a row that is
// not the user's. Drift checks tie those names to the backend (apply_ops.py, preview_ops.py) and to the
// Russian table (i18n/ru.json). Reads sources only; the commands themselves run in tests/test_no_zenity.py.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const PLUGIN = path.join(__dirname, '..');

function loadJs(rel) {
  const src = fs.readFileSync(path.join(PLUGIN, rel), 'utf8').replace(/^\.pragma library\s*$/m, '');
  const ctx = {};
  vm.runInNewContext(src, ctx, { filename: path.join(PLUGIN, rel) });
  return ctx;
}
const inWindow = loadJs('ui/InWindow.js');
const read = (rel) => fs.readFileSync(path.join(PLUGIN, rel), 'utf8');

const OWN = ['presets', 'styles', 'bar-skins', 'bar-layouts'];
const OTHER = ['walls', 'theme-switcher', 'theme-walls', 'dock', 'lock', 'bar-tweaks', 'themes', 'sounds'];

test('only the four categories with own items have save rows and deletable rows', () => {
  for (const c of OWN) assert.equal(inWindow.has(c), true, c);
  for (const c of OTHER) assert.equal(inWindow.has(c), false, c);
});

test('the 💾 row is the value "save" of an own-items category and nothing else', () => {
  for (const c of OWN) {
    assert.equal(inWindow.isSaveRow(c, 'save'), true, c);
    assert.equal(inWindow.isSaveRow(c, 'work'), false, `${c} work`);
  }
  assert.equal(inWindow.isSaveRow('walls', 'save'), false);
  assert.equal(inWindow.isSaveRow('theme-switcher', 'save'), false);
});

test('a new save starts with the name the bare prompt starts with', () => {
  assert.equal(inWindow.defaultSaveName('presets'), 'My Preset');
  assert.equal(inWindow.defaultSaveName('styles'), 'My Style');
  assert.equal(inWindow.defaultSaveName('bar-skins'), 'my-skin');
  assert.equal(inWindow.defaultSaveName('bar-layouts'), 'my-layout');
  assert.equal(inWindow.defaultSaveName('walls'), '');
});

test('each own-items category deletes through its own *-delete command', () => {
  assert.equal(inWindow.removeCommand('presets'), 'preset-delete');
  assert.equal(inWindow.removeCommand('styles'), 'style-delete');
  assert.equal(inWindow.removeCommand('bar-skins'), 'skin-delete');
  assert.equal(inWindow.removeCommand('bar-layouts'), 'layout-delete');
  assert.equal(inWindow.removeCommand('walls'), '');
});

test('the refusal names the kind of item and is empty for other categories', () => {
  assert.equal(inWindow.refusal('presets'), 'Only your own presets (★) can be deleted');
  assert.equal(inWindow.refusal('styles'), 'Only your own styles (★) can be deleted');
  assert.equal(inWindow.refusal('bar-skins'), 'Only your own skins (★) can be deleted');
  assert.equal(inWindow.refusal('bar-layouts'), 'Only your own layouts (★) can be deleted');
  assert.equal(inWindow.refusal('walls'), '');
});

test('the default save names are the ones the backend passes to its zenity prompt', () => {
  const apply = read('backend/customizer/apply_ops.py');
  for (const c of OWN) assert.ok(apply.includes(`--entry-text=${inWindow.defaultSaveName(c)}"`), c);
});

test('each delete command is a backend command and each refusal is the backend text, translated', () => {
  const preview = read('backend/customizer/preview_ops.py');
  const ru = JSON.parse(read('i18n/ru.json'));
  for (const c of OWN) {
    const cmd = inWindow.removeCommand(c);
    assert.ok(preview.includes(`"${cmd}"`), `${cmd} is not a backend command`);
    assert.ok(preview.includes(`t("${inWindow.refusal(c)}")`), `${c}: refusal is not the backend text`);
    assert.ok(Object.prototype.hasOwnProperty.call(ru, inWindow.refusal(c)), `${c}: no ru.json entry`);
  }
});

// setCategory must drop a pending footer question and the notice: a question's yes-callback reads the
// current category when it is answered (submitSave), so it cannot outlive a tab switch.
test('switching tabs drops a pending footer question and the notice', () => {
  const qml = read('Customizer.qml');
  const body = qml.slice(qml.indexOf('function setCategory('), qml.indexOf('function categoryIndexOf('));
  assert.ok(body.includes('root.confirm = null'), 'setCategory keeps a pending question');
  assert.ok(body.includes('root.notice = ""'), 'setCategory keeps the notice');
});
