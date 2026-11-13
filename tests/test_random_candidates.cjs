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
