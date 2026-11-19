// @file Executes the QML eligibility library in Node so action safety stays testable without a compositor.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const sourcePath = path.join(__dirname, '../ui/RandomCandidates.js');
const source = fs.readFileSync(sourcePath, 'utf8').replace(/^\.pragma library\s*$/m, '');
const qmlLibrary = {};
vm.runInNewContext(source, qmlLibrary, { filename: sourcePath });

test('Wallpaper FX random picks allow transitions', () => {
  assert.equal(qmlLibrary.isCandidate('wallpaper-fx', 'outline', false, false), true);
  assert.equal(qmlLibrary.isCandidate('wallpaper-fx', 'outline-cut', false, false), true);
  assert.equal(qmlLibrary.isCandidate('wallpaper-fx', 'fade', false, false), true);
});

test('Wallpaper FX random picks reject one-off actions', () => {
  for (const value of ['outline-install', 'outline-warm', 'owe-toggle', 'enable-plugin']) {
    assert.equal(qmlLibrary.isCandidate('wallpaper-fx', value, false, false), false, value);
  }
});

test('current, selected and generic action rows stay excluded', () => {
  assert.equal(qmlLibrary.isCandidate('themes', 'dark', true, false), false);
  assert.equal(qmlLibrary.isCandidate('themes', 'light', false, true), false);
  assert.equal(qmlLibrary.isCandidate('themes', 'toggle', false, false), false);
  assert.equal(qmlLibrary.isCandidate('themes', 'catppuccin', false, false), true);
});

test('every mapped Wallpaper FX transition is eligible for random picks', () => {
  for (const key of Object.keys(qmlLibrary.WALLPAPER_FX_TRANSITIONS)) {
    assert.equal(qmlLibrary.isCandidate('wallpaper-fx', key, false, false), true, key);
  }
});

test('none and unknown values stay out of Wallpaper FX random picks', () => {
  assert.equal(qmlLibrary.WALLPAPER_FX_TRANSITIONS.none, undefined);
  assert.equal(qmlLibrary.isCandidate('wallpaper-fx', 'none', false, false), false);
  assert.equal(qmlLibrary.isCandidate('wallpaper-fx', 'supernova', false, false), false);
  assert.equal(qmlLibrary.isCandidate('wallpaper-fx', 'random', false, false), true);
});

// Action rows the backend lists per category (swept with `customizer.sh list <cat>`; the lock,
// dock and sounds rows that only appear with their tools or data are listed from the source).
// None may take the random pick. The regex has no marker to read, so each new action row is added here.
test('one-off action rows never take the random pick', () => {
  const actions = [
    ['presets', 'save'], ['styles', 'save'], ['bar-layouts', 'save'], ['bar-skins', 'save'],
    ['dotify', 'current'], ['dotify', 'arch'], ['dotify', 'pick-dir'], ['dotify', 'pick-files'],
    ['walls', 'pick-dir'], ['walls', 'pick-files'],
    ['launcher', 'open'], ['theme-switcher', 'cache'], ['theme-switcher', 'prune'],
    ['glyph', 'test:normal'], ['sounds', 'test:open'],
    ['windows', 'geometry-reset'],
    ['shaders', 'toggle'], ['shaders', 'next'], ['shaders', 'reading'],
    ['dock', 'toggle'], ['dock', 'autohide'], ['dock', 'pin-pick'], ['dock', 'unpin:org.gnome.Nautilus'],
    ['lock', 'regen-thumbs'], ['lock', 'missing-thumbs'],
    ['lock', 'sddm-fetch'], ['lock', 'sddm-fetch-all'], ['lock', 'sddm-login'], ['lock', 'sddm-login-glyph'],
    ['wallpaper-fx', 'owe-toggle'], ['wallpaper-fx', 'outline-install'],
    ['theme-walls', 'dir:/home/user'],
  ];
  for (const [category, value] of actions) {
    assert.equal(qmlLibrary.isCandidate(category, value, false, false), false, `${category} ${value}`);
  }
});

test('settings and choice rows stay eligible next to the action rows', () => {
  const choices = [
    ['dock', 'pos:top'], ['shaders', 'crt'], ['sounds', 'pack:brutal'], ['lock', 'sddm:NieR'],
    ['theme-switcher', 'style:cards'], ['launcher', 'skin:drawer'], ['blur', 'light'], ['themes', 'catppuccin'],
  ];
  for (const [category, value] of choices) {
    assert.equal(qmlLibrary.isCandidate(category, value, false, false), true, `${category} ${value}`);
  }
});
