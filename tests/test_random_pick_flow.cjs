// @file Safe end-to-end test of the filtered random pick (issue #4).
//
// Real backend `list wallpaper-fx` output (sandboxed HOME) → the same parse, filter
// and pick-decision functions Customizer.qml runs → the dispatched command, recorded
// here instead of executed. Mirrors the keyboard flow: "/" + "cut", Enter leaves the
// filter input while keeping the filter, then "r" picks. Never runs outline-install
// or touches user wallpaper/config state.
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const PLUGIN = path.join(__dirname, '..');

function loadJs(rel) {
  const p = path.join(PLUGIN, rel);
  const src = fs.readFileSync(p, 'utf8').replace(/^\.pragma library\s*$/m, '');
  const lib = {};
  vm.runInNewContext(src, lib, { filename: p });
  return lib;
}
const candidates = loadJs('ui/RandomCandidates.js');
const flow = loadJs('ui/RandomPickFlow.js');

// Fresh HOME with the Wallpaper FX plugin enabled; every XDG path stays inside it.
// Language is pinned to English both ways (customizer.json "lang" wins over locale,
// LC_ALL backs it up) because the filter fixture matches English row labels.
function sandbox(fxType) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'fx-flow-'));
  const cfg = path.join(home, '.config', 'omarchy');
  fs.mkdirSync(cfg, { recursive: true });
  fs.mkdirSync(path.join(home, 'run'), { recursive: true });
  fs.writeFileSync(path.join(cfg, 'shell.json'),
    JSON.stringify({ plugins: [{ id: 'kamradsmeshnyavy.background' }] }));
  fs.writeFileSync(path.join(cfg, 'customizer.json'), JSON.stringify({ lang: 'en' }));
  if (fxType) {
    fs.writeFileSync(path.join(cfg, 'wallpaper-transition.json'), JSON.stringify({ type: fxType }));
  }
  return home;
}

// Read-only backend list; the sandbox keeps it away from real config and state.
function listWallpaperFx(home) {
  return execFileSync('/usr/bin/python3', ['-I', path.join(PLUGIN, 'backend/run.py'),
    'list', 'wallpaper-fx'], {
    env: {
      ...process.env,
      HOME: home,
      LC_ALL: 'C',
      XDG_CONFIG_HOME: path.join(home, '.config'),
      XDG_CACHE_HOME: path.join(home, '.cache'),
      XDG_STATE_HOME: path.join(home, '.local', 'state'),
      XDG_RUNTIME_DIR: path.join(home, 'run'),
    },
    encoding: 'utf8',
  });
}

// `/` opens the filter, "cut" narrows the list, Enter keeps the filter: these are
// the rows the overlay would display when `r` is pressed.
function filteredFxRows(home) {
  return flow.filterRows(flow.parseRows(listWallpaperFx(home)), 'cut');
}

function indexOfValue(rows, value) {
  return rows.findIndex((r) => r.value === value);
}

test('the cut filter shows the transition and the install action rows', () => {
  const rows = filteredFxRows(sandbox('slant'));
  assert.ok(indexOfValue(rows, 'outline-cut') >= 0, 'outline-cut row');
  assert.ok(indexOfValue(rows, 'outline-install') >= 0, 'outline-install row');
});

test('r dispatches only the eligible transition, never outline-install', () => {
  const rows = filteredFxRows(sandbox('slant'));
  const dispatched = [];
  const pick = flow.decideRandomPick(candidates.isCandidate, 'wallpaper-fx', rows, -1, 0);
  if (pick) dispatched.push(Array.from(flow.applyCommand('customizer.sh', 'wallpaper-fx', pick.value)));
  assert.deepEqual(dispatched, [['customizer.sh', 'apply', 'wallpaper-fx', 'outline-cut']]);
});

test('highlighted install row: r still dispatches only the non-current transition', () => {
  const rows = filteredFxRows(sandbox('slant'));
  const install = indexOfValue(rows, 'outline-install');
  assert.ok(install >= 0, 'install row visible');
  for (const rand of [0, 0.25, 0.5, 0.75, 0.999]) {
    const pick = flow.decideRandomPick(candidates.isCandidate, 'wallpaper-fx', rows, install, rand);
    assert.ok(pick, 'a transition remains eligible');
    assert.equal(pick.value, 'outline-cut');
  }
});

test('no eligible transition: r is a no-op and nothing is dispatched', () => {
  // outline-cut is current, so filtering to "cut" leaves no eligible transition.
  const rows = filteredFxRows(sandbox('outline-cut'));
  const dispatched = [];
  const selections = [-1, indexOfValue(rows, 'outline-install'), indexOfValue(rows, 'outline-cut')];
  for (const selected of selections) {
    const pick = flow.decideRandomPick(candidates.isCandidate, 'wallpaper-fx', rows, selected, 0);
    assert.equal(pick, null);
    if (pick) dispatched.push(Array.from(flow.applyCommand('customizer.sh', 'wallpaper-fx', pick.value)));
  }
  assert.deepEqual(dispatched, []);
});

test('filter helpers keep section headers above visible rows only', () => {
  const rows = filteredFxRows(sandbox('slant'));
  for (const value of ['section:transitions', 'section:actions']) {
    const at = indexOfValue(rows, value);
    assert.ok(at >= 0 && rows[at + 1] && !flow.isHeader(rows[at + 1]), value);
  }
});

test('Customizer.qml wires the production pick and dispatch through the shared flow', () => {
  const qml = fs.readFileSync(path.join(PLUGIN, 'Customizer.qml'), 'utf8');
  assert.ok(qml.includes('RandomPickFlow.decideRandomPick('), 'randomPick uses decideRandomPick');
  assert.ok(qml.includes('Quickshell.execDetached(RandomPickFlow.applyCommand('),
    'apply dispatch builds the tested command');
});

test('the backend writes its runtime directory inside the sandbox', () => {
  const home = sandbox('slant');
  filteredFxRows(home);
  assert.ok(fs.existsSync(path.join(home, 'run', 'omarchy-customizer')),
    'XDG_RUNTIME_DIR override keeps paths.RUN in the fixture HOME');
});
