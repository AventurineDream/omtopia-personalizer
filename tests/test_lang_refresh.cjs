// @file Language change picked up without a shell restart (overlay is keepLoaded).
//
// Backend half: `customizer.sh lang` is a fresh process per call and must follow
// "lang" in customizer.json (sandboxed HOME). QML half: open() re-runs langProc, the
// handler reloads i18n/<lang>.json even when its path is unchanged (ru → en → ru),
// and a language change drops the backend-translated search index.
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PLUGIN = path.join(__dirname, '..');

function sandbox() {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'lang-refresh-'));
  const cfg = path.join(home, '.config', 'omarchy');
  fs.mkdirSync(cfg, { recursive: true });
  fs.mkdirSync(path.join(home, 'run'), { recursive: true });
  return home;
}

function langOf(home) {
  return execFileSync(path.join(PLUGIN, 'customizer.sh'), ['lang'], {
    env: { PATH: process.env.PATH, HOME: home, XDG_RUNTIME_DIR: path.join(home, 'run'), LANG: 'en_US.UTF-8' },
    encoding: 'utf8',
  }).trim();
}

test('the lang command follows customizer.json in each fresh process', () => {
  const home = sandbox();
  const cfg = path.join(home, '.config', 'omarchy', 'customizer.json');
  fs.writeFileSync(cfg, JSON.stringify({ lang: 'en' }));
  assert.equal(langOf(home), 'en');
  fs.writeFileSync(cfg, JSON.stringify({ lang: 'ru' }));
  assert.equal(langOf(home), 'ru');
  fs.writeFileSync(cfg, JSON.stringify({ lang: 'en' }));
  assert.equal(langOf(home), 'en');
});

test('Customizer.qml re-reads the language on every open()', () => {
  const qml = fs.readFileSync(path.join(PLUGIN, 'Customizer.qml'), 'utf8');
  const start = qml.indexOf('function open(payloadJson) {');
  assert.ok(start >= 0, 'open() exists');
  const body = qml.slice(start, qml.indexOf('\n  }\n', start));
  assert.ok(body.includes('langProc.running = true'), 'open() restarts langProc');
});

test('langProc reloads the same i18n file and drops stale search labels on change', () => {
  const qml = fs.readFileSync(path.join(PLUGIN, 'Customizer.qml'), 'utf8');
  const start = qml.indexOf('id: langProc');
  const handler = qml.slice(start, qml.indexOf('FileView {', start));
  assert.ok(handler.includes('i18nFile.reload()'), 'same path is reloaded, not skipped');
  assert.ok(handler.includes('root.searchIndex = []'), 'search index is refetched after a change');
});
