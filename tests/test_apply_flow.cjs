// @file Tests for the stay-open decision of applies (ui/ApplyFlow.js).
//
// Table of apply values: dialog / surface values must close the overlay, ordinary values keep it
// open. The probe (tests/apply_surface_probe.py) runs apply_ops.apply() for every listed row with
// subprocess and the surface helpers replaced, and the table must agree with what each apply opens.
// Drift checks: every Wallpaper FX transition in the backend catalog keeps the overlay open, and every
// category that apply_ops.apply() branches on must have a stay-open rule.
// Never runs a real apply: the probe runs in a temp HOME with recorders.
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const PLUGIN = path.join(__dirname, '..');

function loadJs(rel) {
  const p = path.join(PLUGIN, rel);
  const src = fs.readFileSync(p, 'utf8').replace(/^\.pragma library\s*$/m, '');
  const ctx = {};
  // QML's `.import "x.js" as Y` binds the library to Y; here the library is loaded into Y.
  const body = src.replace(/^\.import "([^"]+)" as (\w+)\s*$/gm, (_m, file, name) => {
    ctx[name] = loadJs(path.posix.join(path.posix.dirname(rel), file));
    return '';
  });
  vm.runInNewContext(body, ctx, { filename: p });
  return ctx;
}
const flow = loadJs('ui/ApplyFlow.js');

function keeps(category, value) {
  return flow.keepsOpen(category, value);
}

// Values that open a dialog, a terminal, a lock preview, the launcher or the picker, or change
// the loaded plugins. Each one must close the overlay.
const CLOSING = [
  ['presets', 'save'],
  ['presets', 'tweak:window.gaps'],
  ['styles', 'save'],
  ['styles', 'tweak:style.font'],
  ['bar-skins', 'save'],
  ['bar-layouts', 'save'],
  ['walls', 'pick-dir'],
  ['walls', 'pick-files'],
  ['dotify', 'pick-dir'],
  ['dotify', 'pick-files'],
  ['dotify', 'tweak:dotify.color'],
  ['theme-switcher', 'prune'],
  ['theme-switcher', 'tweak:picker.size'],
  ['lock', 'sddm-login-glyph'],
  ['lock', 'sddm-login'],
  ['lock', 'sddm-fetch-all'],
  ['lock', 'sddm-fetch'],
  ['lock', 'regen-thumbs'],
  ['lock', 'missing-thumbs'],
  ['launcher', 'open'],
  ['launcher', 'tweak:menu.color'],
  ['dock', 'toggle'],
  ['dock', 'pin-pick'],
  ['wallpaper-fx', 'outline-install'],
  ['wallpaper-fx', 'enable-plugin'],
  ['wallpaper-fx', 'tweak:fx.speed'],
  ['wallpaper-fx', 'outline-open'],
  ['windows', 'tweak:windowGapsIn'],
  ['bar-tweaks', 'tweak:background'],
  ['bar-tweaks', 'tweak:text'],
  ['lock-tweaks', 'tweak:lockClock'],
  ['widgets', 'tweak:w:clock'],
  ['dashboard', 'tweak:dashWeather'],
  ['osd', 'tweak:osdBackground'],
  ['notifications', 'tweak:notifyBackground'],
  ['glyph', 'tweak:glyphColor'],
  ['shaders', 'tweak:shaderSpeed'],
  ['sounds', 'tweak:soundVolume'],
  ['bar-widgets', 'w:clock'],
  ['no-such-category', 'anything'],
  ['anims', ''],
];

// Ordinary applies: a theme, wallpaper, preset, file or preset name. Each must keep the overlay open.
const OPEN = [
  ['anims', '/home/u/.config/omarchy/customizer/animations/snappy.lua'],
  ['opacity', 'subtle'],
  ['blur', 'medium'],
  ['bar-skins', '/home/u/.config/omarchy/customizer/skins/night.json'],
  ['bar-layouts', '/home/u/.config/omarchy/customizer/layouts/left.json'],
  ['themes', 'catppuccin'],
  ['themes', 'dynamic:light'],
  ['theme-walls', '/home/u/Pictures/Walls/dune.png'],
  ['fonts', 'mono-classic'],
  ['sounds', 'pack:retro'],
  ['sounds', 'test:notify'],
  ['styles', '/home/u/.config/omarchy/customizer/styles/soft.json'],
  ['presets', '/home/u/.config/omarchy/customizer/presets/work.json'],
  ['presets', 'geometry-reset'],
  ['windows', 'geometry-reset'],
  ['walls', '/home/u/Pictures/Walls/dune.png'],
  ['dotify', 'current'],
  ['dotify', 'arch'],
  ['dotify', '/home/u/Pictures/a.png'],
  ['glyph', 'test:normal'],
  ['glyph', 'test:charge'],
  ['launcher', 'skin:frosted'],
  ['theme-switcher', 'cache'],
  ['theme-switcher', 'style:grid'],
  ['lock', 'my:clock-lite'],
  ['dock', 'pos:bottom'],
  ['dock', 'autohide'],
  ['dock', 'unpin:org.gnome.Nautilus'],
  ['shaders', 'toggle'],
  ['shaders', 'next'],
  ['shaders', 'crt-static'],
  ['shaders', 'reading'],
  ['wallpaper-fx', 'slant'],
  ['wallpaper-fx', 'outline-cut'],
  ['wallpaper-fx', 'random'],
  ['wallpaper-fx', 'none'],
  ['wallpaper-fx', 'owe-toggle'],
  ['wallpaper-fx', 'outline-warm'],
  ['wallpaper-fx', 'outline-status'],
];

test('dialog, terminal, surface and plugin-changing values close the overlay', () => {
  for (const [category, value] of CLOSING) {
    assert.equal(keeps(category, value), false, `${category} ${value} must close`);
  }
});

test('ordinary applies keep the overlay open', () => {
  for (const [category, value] of OPEN) {
    assert.equal(keeps(category, value), true, `${category} ${value} must stay open`);
  }
});

test('an unknown Wallpaper FX action closes the overlay', () => {
  assert.equal(keeps('wallpaper-fx', 'outline-rebuild'), false);
  assert.equal(keeps('wallpaper-fx', 'outline-install'), false);
  assert.equal(keeps('wallpaper-fx', 'random-action'), false);
});

test('the empty value and a missing value close the overlay', () => {
  assert.equal(keeps('themes', ''), false);
  assert.equal(keeps('themes', undefined), false);
  assert.equal(keeps('themes', null), false);
});

// Reads the Wallpaper FX transition values from the backend catalog (the drift guard for the table).
function catalogTransitions() {
  const out = execFileSync('/usr/bin/python3', ['-I', '-c',
    'import sys; sys.path.insert(0, "backend"); from customizer import fx_catalog as f; '
    + 'print("\\n".join(v for v, _d, _ok in f.FX_EFFECTS))'], { cwd: PLUGIN, encoding: 'utf8' });
  return out.split('\n').filter(Boolean);
}

test('every catalog transition keeps a wallpaper-fx apply open', () => {
  const closed = catalogTransitions().filter((v) => !keeps('wallpaper-fx', v));
  assert.deepEqual(closed, []);
});

// Each category name apply_ops.apply() branches on (`category == "x"` and `category in (...)`).
function applyCategories() {
  const src = fs.readFileSync(path.join(PLUGIN, 'backend/customizer/apply_ops.py'), 'utf8');
  const names = new Set();
  for (const m of src.matchAll(/category == "([^"]+)"/g)) names.add(m[1]);
  for (const m of src.matchAll(/category in \(([^)]*)\)/g))
    for (const n of m[1].matchAll(/"([^"]+)"/g)) names.add(n[1]);
  return [...names].sort();
}

test('every category apply_ops.apply() branches on has a stay-open rule', () => {
  const missing = applyCategories().filter((c) => !Object.prototype.hasOwnProperty.call(flow.RULES, c));
  assert.deepEqual(missing, []);
});

// Categories the probe cannot list in the test sandbox, with the reason. Any other rule category
// without probed rows fails the probe test below.
const UNPROBED = {
  fonts: 'lists nothing unless omarchy-font-profile is installed, and the test host has none',
  'theme-walls': 'lists only a header row unless a current theme with backgrounds exists',
};

// Categories with no apply_ops branch, with the reason. Their rows are sent to tweak() by the UI.
const NO_APPLY_BRANCH = {
  'bar-widgets': 'bar-widget rows (w:, wset:) are tweaks handled by tweak(); apply() has no branch',
};

function probeResults() {
  const out = execFileSync('/usr/bin/python3', ['-I', 'tests/apply_surface_probe.py'],
    { cwd: PLUGIN, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  return JSON.parse(out);
}

test('the stay-open table matches the surfaces apply_ops.apply() opens for every listed row', () => {
  const probe = probeResults();
  assert.deepEqual(probe.errors, {}, 'a category could not be listed');
  assert.ok(probe.results.length > 300, `probe applied only ${probe.results.length} rows`);
  // A row that fails with a non-exit error may have opened its surface before failing.
  const failed = probe.results.filter((r) => r.error && !r.error.startsWith('Exit('))
    .map((r) => `${r.category} ${JSON.stringify(r.value)}: ${r.error}`);
  assert.deepEqual(failed, []);
  const probed = new Set(probe.results.map((r) => r.category));
  const unprobed = Object.keys(flow.RULES).filter((c) => !probed.has(c)).sort();
  assert.deepEqual(unprobed, Object.keys(UNPROBED).sort());
  // Categories apply_ops.apply() has no branch for: the UI sends their rows through tweak(), never run(),
  // so apply() is a no-op for them. They must close (the fail-closed default) and make no calls.
  for (const r of probe.results.filter((x) => NO_APPLY_BRANCH[x.category] !== undefined)) {
    assert.equal(keeps(r.category, r.value), false, `${r.category} ${r.value}: must close`);
    assert.deepEqual(r.calls, [], `${r.category} ${r.value}: apply() made calls`);
  }
  // Stay open exactly when no surface is opened: keepsOpen must be the negation of surface.
  const wrong = probe.results.filter((r) => NO_APPLY_BRANCH[r.category] === undefined)
    .filter((r) => keeps(r.category, r.value) === r.surface).map((r) =>
    `${r.category} ${JSON.stringify(r.value)}: keepsOpen=${keeps(r.category, r.value)}, surface=${r.surface}, ` +
    `surfaces=${JSON.stringify(r.surfaces)}, calls=${JSON.stringify(r.calls)}`);
  assert.deepEqual(wrong, []);
});

// Applies whose bare form opens zenity. The probe's surface marks name the zenity helpers and the bare
// save helpers (the probe replaces them with recorders, so each one is a surface).
const ZENITY_SURFACES = ['_zenity', '_pick_dir', '_pick_images',
  'save_user_preset', 'save_user_style', 'save_user_skin', 'save_user_layout'];

test('needsZenity names exactly the applies whose surface is zenity', () => {
  const probe = probeResults();
  const wrong = probe.results
    // Colour, text, file and folder tweak rows depend on the row's kind: Customizer.qml checks those itself.
    .filter((r) => !String(r.value).startsWith('tweak:'))
    .filter((r) => flow.needsZenity(r.category, r.value)
      !== (r.surfaces || []).some((s) => ZENITY_SURFACES.includes(s)))
    .map((r) => `${r.category} ${JSON.stringify(r.value)}: needsZenity=${flow.needsZenity(r.category, r.value)}, ` +
      `surfaces=${JSON.stringify(r.surfaces)}`);
  assert.deepEqual(wrong, []);
});

test('needsZenity covers every zenity-only form the overlay can reach, and no in-window or plain form', () => {
  const ZENITY = [['presets', 'save'], ['styles', 'save'], ['bar-skins', 'save'], ['bar-layouts', 'save'],
    ['walls', 'pick-dir'], ['walls', 'pick-files'], ['dotify', 'pick-dir'], ['dotify', 'pick-files'],
    ['dock', 'pin-pick'], ['lock', 'sddm-fetch'], ['theme-switcher', 'prune']];
  for (const [category, value] of ZENITY) assert.equal(flow.needsZenity(category, value), true, `${category} ${value}`);
  assert.equal(flow.needsZenity('presets', '/home/u/.config/omarchy/customizer/presets/work.json'), false);
  assert.equal(flow.needsZenity('walls', '/home/u/Pictures/Walls/dune.png'), false);
  assert.equal(flow.needsZenity('theme-switcher', 'cache'), false);
  assert.equal(flow.needsZenity('bar-skins', '/home/u/.config/omarchy/bar-skins/night.json'), false);
});