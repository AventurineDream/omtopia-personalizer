// @file Backend half of the language refresh: `customizer.sh lang` is a fresh process per
// call and must follow "lang" in customizer.json (sandboxed HOME). The QML half (open()
// re-reading the language, same-path reload) is verified in an omabox box, not by source
// matching.
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
