// @file Tests for the stay-open decision of applies (ui/ApplyFlow.js).
//
// Table of apply values: dialog / surface values must close the overlay, ordinary values keep it
// open. Drift checks: every Wallpaper FX transition in the backend catalog keeps the overlay open,
// and every category that apply_ops.apply() branches on must have a stay-open rule.
// Never runs an apply: only the pure decision function is exercised.
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
