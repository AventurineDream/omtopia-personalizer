// @file Tests for the in-window save and delete rules and the overlay decisions kept in ui/InWindow.js: which
// categories have a 💾 save row, the name a new save starts with, the delete command and its refusal, the key
// route, the outcome of a save, the reset on a tab switch and the order of queued writes.
// The backend checks run the real backend (backend/run.py) in a temp HOME. zenity is a stub that logs its
// arguments and cancels; notify-send, gio and hyprctl are logging stubs, so nothing reaches the desktop.
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const PLUGIN = path.join(__dirname, '..');
const RUN = path.join(PLUGIN, 'backend/run.py');

function loadJs(rel) {
  const src = fs.readFileSync(path.join(PLUGIN, rel), 'utf8').replace(/^\.pragma library\s*$/m, '');
  const ctx = {};
  vm.runInNewContext(src, ctx, { filename: path.join(PLUGIN, rel) });
  return ctx;
}
const inWindow = loadJs('ui/InWindow.js');

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

test('each refusal and the 💾 label of the layouts have a Russian translation', () => {
  const ru = JSON.parse(fs.readFileSync(path.join(PLUGIN, 'i18n/ru.json'), 'utf8'));
  for (const c of OWN) assert.ok(Object.prototype.hasOwnProperty.call(ru, inWindow.refusal(c)), `${c} refusal`);
  assert.ok(Object.prototype.hasOwnProperty.call(ru, '💾 Save the current one as a layout…'));
});

test('a footer question takes the key first, then an open field, then the overlay', () => {
  assert.equal(inWindow.keyRoute(true, true), 'confirm');
  assert.equal(inWindow.keyRoute(false, true), 'confirm');
  assert.equal(inWindow.keyRoute(true, false), 'field');
  assert.equal(inWindow.keyRoute(false, false), 'overlay');
});

test('a tab switch or Home clears the footer question and the notice, and nothing else', () => {
  const o = { confirm: { text: 'Overwrite Zen?', yesLabel: 'overwrite', yes: () => {} }, notice: 'a notice', editingIndex: 4 };
  inWindow.clearTransient(o);
  assert.equal(o.confirm, null);
  assert.equal(o.notice, '');
  assert.equal(o.editingIndex, 4);
});

test('a save result: 0 saved, 3 taken (the overlay asks to overwrite), any other code failed', () => {
  assert.equal(inWindow.saveOutcome(0), 'saved');
  assert.equal(inWindow.saveOutcome(3), 'taken');
  assert.equal(inWindow.saveOutcome(1), 'failed');
  assert.equal(inWindow.saveOutcome(2), 'failed');
});

test('queued writes run in the order they were asked for', () => {
  assert.equal(inWindow.nextLane(-1, -1), 'none');
  assert.equal(inWindow.nextLane(5, -1), 'apply');
  assert.equal(inWindow.nextLane(-1, 2), 'tweak');
  assert.equal(inWindow.nextLane(3, 4), 'apply', 'a save asked before a tweak step runs first');
  assert.equal(inWindow.nextLane(7, 4), 'tweak', 'a tweak step asked before a save runs first');
});

// ── Backend: the real run.py in a temp HOME; the stubs log to one file ──

function sandbox() {
  const base = fs.mkdtempSync(path.join(process.env.XDG_RUNTIME_DIR || os.tmpdir(), 'in-window.'));
  const home = path.join(base, 'home');
  const bin = path.join(base, 'bin');
  const log = path.join(base, 'calls.log');
  fs.mkdirSync(home);
  fs.mkdirSync(bin);
  fs.writeFileSync(path.join(bin, 'zenity'), `#!/bin/sh\nprintf 'zenity %s\\n' "$*" >> "${log}"\nexit 1\n`, { mode: 0o755 });
  for (const name of ['notify-send', 'gio', 'hyprctl']) {
    fs.writeFileSync(path.join(bin, name), `#!/bin/sh\nprintf '${name} %s\\n' "$*" >> "${log}"\n`, { mode: 0o755 });
  }
  const env = {
    PATH: `${bin}:/usr/bin:/bin`, HOME: home, LC_ALL: 'C',
    XDG_STATE_HOME: path.join(home, '.local/state'), XDG_CACHE_HOME: path.join(home, '.cache'),
    XDG_RUNTIME_DIR: base, OMARCHY_PATH: path.join(base, 'omarchy'),
  };
  return { base, home, log, env };
}

function backend(env, args) {
  try {
    return { code: 0, out: execFileSync('/usr/bin/python3', ['-I', RUN, ...args], { env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }), err: '' };
  } catch (e) {
    return { code: e.status, out: e.stdout || '', err: e.stderr || '' };
  }
}

test('the bare save prompt starts with the name the 💾 row starts with', () => {
  const sb = sandbox();
  try {
    for (const c of OWN) {
      backend(sb.env, ['apply', c, 'save']);
      const log = fs.readFileSync(sb.log, 'utf8');
      assert.ok(log.includes(`--entry-text=${inWindow.defaultSaveName(c)}\n`), `${c}: ${log}`);
      fs.rmSync(sb.log, { force: true });
    }
  } finally {
    fs.rmSync(sb.base, { recursive: true, force: true });
  }
});

test('each delete command refuses a file outside the user folder with the reason the footer shows', () => {
  const sb = sandbox();
  try {
    const outside = path.join(sb.home, 'Downloads', 'shared.json');
    fs.mkdirSync(path.dirname(outside), { recursive: true });
    fs.writeFileSync(outside, '{}\n');
    for (const c of OWN) {
      const r = backend(sb.env, [inWindow.removeCommand(c), outside, '--yes']);
      assert.equal(r.code, 1, c);
      assert.ok(r.out.includes(inWindow.refusal(c)), `${c}: ${r.out}${r.err}`);
      assert.equal(fs.existsSync(outside), true, c);
    }
  } finally {
    fs.rmSync(sb.base, { recursive: true, force: true });
  }
});

test('a save exits with the code the overlay reads: saved, taken, or failed with the reason', () => {
  const sb = sandbox();
  try {
    const first = backend(sb.env, ['apply', 'presets', 'save', '--name', 'Zen Check']);
    assert.equal(inWindow.saveOutcome(first.code), 'saved');
    const again = backend(sb.env, ['apply', 'presets', 'save', '--name', 'Zen Check']);
    assert.equal(inWindow.saveOutcome(again.code), 'taken');
    assert.ok(again.err.includes('already exists'), again.err);
    const bad = backend(sb.env, ['apply', 'presets', 'save', '--name', 'Работа']);
    assert.equal(inWindow.saveOutcome(bad.code), 'failed');
    assert.ok(bad.err.includes('Use latin letters, digits, - and _ only'), bad.err);
  } finally {
    fs.rmSync(sb.base, { recursive: true, force: true });
  }
});

test('the Bar Layout 💾 row is a layout save row', () => {
  const sb = sandbox();
  try {
    const first = backend(sb.env, ['list', 'bar-layouts']).out.split('\n')[0].split('\t');
    assert.equal(first[0], '💾 Save the current one as a layout…');
    assert.equal(first[1], 'save');
  } finally {
    fs.rmSync(sb.base, { recursive: true, force: true });
  }
});
