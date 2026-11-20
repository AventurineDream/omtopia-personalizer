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
// Sandboxes live in os.tmpdir() (RAM here). They are removed when the file passes and kept,
// with their paths printed, when it fails. Node sets the exit code from the test results.
const sandboxes = [];
process.on('exit', (code) => {
  for (const home of sandboxes) {
    if (code === 0) {
      try {
        fs.rmSync(home, { recursive: true, force: true });
      } catch (err) {
        console.error('could not remove sandbox ' + home + ': ' + err.message);
      }
    } else {
      console.error('sandbox kept: ' + home);
    }
  }
});

// Fresh HOME with the Wallpaper FX plugin enabled; every XDG path stays inside it.
// Language is pinned to English both ways (customizer.json "lang" wins over locale,
// LC_ALL backs it up) because the filter fixture matches English row labels.
function sandbox(fxType) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'fx-flow-'));
  sandboxes.push(home);
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

// Read-only backend list of one category; the sandbox keeps it away from real config and state.
function listRows(home, category) {
  return execFileSync('/usr/bin/python3', ['-I', path.join(PLUGIN, 'backend/run.py'),
    'list', category], {
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
  return flow.filterRows(flow.parseRows(listRows(home, 'wallpaper-fx')), 'cut');
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
  assert.ok(qml.includes('RandomPickFlow.applyCommand(root.script, key, value)'),
    'enqueueApply builds the tested command');
});

test('the backend writes its runtime directory inside the sandbox', () => {
  const home = sandbox('slant');
  filteredFxRows(home);
  assert.ok(fs.existsSync(path.join(home, 'run', 'omarchy-customizer')),
    'XDG_RUNTIME_DIR override keeps paths.RUN in the fixture HOME');
});

// `r` over a spread of random draws: every value it can pick on this list.
function pickedValues(category, rows, selected) {
  const values = new Set();
  for (let i = 0; i <= 20; i++) {
    const pick = flow.decideRandomPick(candidates.isCandidate, category, rows, selected, i / 21);
    if (pick) values.add(pick.value);
  }
  return values;
}

test('r on Windows never picks the geometry reset', () => {
  const rows = flow.parseRows(listRows(sandbox(null), 'windows'));
  assert.ok(rows.some((r) => r.value === 'geometry-reset'), 'reset row listed');
  assert.deepEqual([...pickedValues('windows', rows, -1)], []);
});

test('r on Dock picks only a dock edge, never pin, unpin, auto-hide or the dock toggle', () => {
  const rows = flow.parseRows(listRows(sandbox(null), 'dock'));
  assert.ok(rows.some((r) => r.value === 'pin-pick'), 'pin row listed');
  const picked = [...pickedValues('dock', rows, -1)];
  assert.ok(picked.length > 0 && picked.every((v) => v.startsWith('pos:')), picked.join(' '));
});

test('r on Shader never picks Reading mode, toggle or next', () => {
  const rows = flow.parseRows(listRows(sandbox(null), 'shaders'));
  assert.ok(rows.some((r) => r.value === 'reading'), 'reading mode row listed');
  const picked = pickedValues('shaders', rows, -1);
  for (const value of ['reading', 'toggle', 'next']) assert.equal(picked.has(value), false, value);
  assert.ok(picked.has('crt'), 'a shader is still picked');
});

test('r on Sounds picks a sound pack, never a test event or the current pack', () => {
  const rows = flow.parseRows(listRows(sandbox(null), 'sounds'));
  const picked = [...pickedValues('sounds', rows, -1)];
  assert.ok(picked.length > 0 && picked.every((v) => v.startsWith('pack:') && v !== 'pack:theme'), picked.join(' '));
});

// The Surprise me button is shown iff canRandomPick says r has a row to pick; both run the same
// candidate rule on the same displayed rows, so the button and the key cannot disagree.
function shown(category, rows, selected) {
  return flow.canRandomPick(candidates.isCandidate, category, rows, selected);
}

test('Surprise me hidden on Windows: the list is only tweak rows and the geometry reset', () => {
  const rows = flow.parseRows(listRows(sandbox(null), 'windows'));
  assert.ok(rows.some((r) => r.value === 'geometry-reset'), 'reset row listed');
  assert.ok(rows.every((r) => r.value.startsWith('section:') || r.value.startsWith('tweak:') || r.value === 'geometry-reset'),
    rows.map((r) => r.value).join(' '));
  assert.equal(shown('windows', rows, -1), false);
  assert.equal(flow.decideRandomPick(candidates.isCandidate, 'windows', rows, -1, 0), null);
});

test('Surprise me shown on Dock: a dock edge can be picked, action rows alone cannot', () => {
  const rows = flow.parseRows(listRows(sandbox(null), 'dock'));
  assert.equal(shown('dock', rows, -1), true);
  const actionsOnly = rows.filter((r) => !r.value.startsWith('pos:'));
  assert.ok(actionsOnly.length > 0 && actionsOnly.length < rows.length, 'list has both kinds');
  assert.equal(shown('dock', actionsOnly, -1), false);
});

test('Surprise me shown on Sounds when a pack other than the current one exists', () => {
  const rows = flow.parseRows(listRows(sandbox(null), 'sounds'));
  assert.equal(shown('sounds', rows, -1), true);
});

test('Surprise me hidden when the list is empty', () => {
  assert.equal(shown('dock', [], -1), false);
  assert.equal(shown('sounds', flow.parseRows(''), -1), false);
});

test('Surprise me hidden when the only eligible row is current or highlighted', () => {
  const row = (value, current) => ({ label: value, value, current });
  const rows = [row('pos:top', false), row('pos:bottom', true)];
  assert.equal(shown('dock', rows, -1), true, 'pos:top is eligible');
  assert.equal(shown('dock', rows, 0), false, 'highlighting pos:top leaves only the current row');
  assert.equal(shown('dock', [row('pos:bottom', true)], -1), false, 'only the current row');
});

test('the button rule and the key agree for every highlight position', () => {
  const rows = flow.parseRows(listRows(sandbox(null), 'dock'));
  for (let s = -1; s < rows.length; s++) {
    const pick = flow.decideRandomPick(candidates.isCandidate, 'dock', rows, s, 0.5);
    assert.equal(shown('dock', rows, s), pick !== null, `selected ${s}`);
  }
});

// The footer's r hint and the Surprise me button both ask randomAvailable (category refusal, then the row
// rule), so these checks cover the hint's decision on the real backend rows.
function gate(category, tweak, rows, selected = -1) {
  return flow.randomAvailable(candidates.isCandidate, category, tweak, rows, selected);
}

test('r hint hidden on Windows, where every row is a tweak or the geometry reset', () => {
  const rows = flow.parseRows(listRows(sandbox(null), 'windows'));
  assert.equal(gate('windows', false, rows), false);
});

test('r hint shown on Dock and Sounds, where a candidate row exists', () => {
  assert.equal(gate('dock', false, flow.parseRows(listRows(sandbox(null), 'dock'))), true);
  assert.equal(gate('sounds', false, flow.parseRows(listRows(sandbox(null), 'sounds'))), true);
});

test('r hint hidden in refused categories and tweak categories, even with candidate rows', () => {
  const dock = flow.parseRows(listRows(sandbox(null), 'dock'));
  for (const category of ['walls', 'dotify', 'presets', 'styles', 'glyph']) {
    assert.equal(gate(category, false, dock), false, category);
  }
  assert.equal(gate('dock', true, dock), false, 'tweak category');
});
