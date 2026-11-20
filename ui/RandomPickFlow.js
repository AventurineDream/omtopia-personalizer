/** @file Filtered random-pick flow: row parsing, the overlay filter, and the pick decision.
 *
 * Shared between Customizer.qml and tests/test_random_pick_flow.cjs, so the headless
 * integration test exercises the same code the shell runs. Pure functions only:
 * nothing here spawns a process or touches wallpaper/config state.
 */
.pragma library

// Backend TSV row → overlay row. Field order matches `list <category>` output;
// 7–10: tweak type, its args, raw value, name without value (list_tweaks).
function parseRows(raw) {
  var rows = []
  var lines = String(raw || "").split("\n")
  for (var i = 0; i < lines.length; i++) {
    if (!lines[i]) continue
    var f = lines[i].split("\t")
    rows.push({ label: f[0] || "", value: f[1] || "", preview: f[2] || "", current: f[3] === "1",
      note: (f[4] || "").replace(/\\n/g, "\n"), sub: f[5] || "",
      kind: f[6] || "", args: f[7] || "", raw: f[8] || "", name: f[9] || "" })
  }
  return rows
}

// Section header row in a settings list: value "section:<name>".
function isHeader(row) { return row !== null && row !== undefined && /^section:/.test(String(row.value || "")) }

// Rows under a filter. A section-name match shows the whole section; a header stays
// while at least one row beneath it is visible. needle is already lowercased.
function filterRows(rows, needle) {
  if (!needle) return rows
  var out = [], header = null, headerHit = false, headerShown = false
  for (var i = 0; i < rows.length; i++) {
    var row = rows[i]
    if (isHeader(row)) {
      header = row
      headerHit = row.label.toLowerCase().indexOf(needle) !== -1
      headerShown = false
      continue
    }
    if (!headerHit && row.label.toLowerCase().indexOf(needle) === -1) continue
    if (header && !headerShown) { out.push(header); headerShown = true }
    out.push(row)
  }
  return out
}

// Indexes of rows the keyboard random action may pick, in display order.
// isCandidate is injected (RandomCandidates.isCandidate) so eligibility keeps one home.
function candidateIndexes(isCandidate, categoryKey, rows, selectedIndex) {
  var out = []
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i]
    if (!isCandidate(categoryKey, r.value, r.current, i === selectedIndex)) continue
    out.push(i)
  }
  return out
}

// The `r` decision over the filtered, displayed rows: the chosen row, or null when
// nothing is eligible — null means no dispatch at all. A supplied rand in [0, 1)
// makes the pick deterministic in tests; the shell passes none and gets Math.random().
function decideRandomPick(isCandidate, categoryKey, rows, selectedIndex, rand) {
  var c = candidateIndexes(isCandidate, categoryKey, rows, selectedIndex)
  if (c.length === 0) return null
  var i = c[Math.floor((rand === undefined ? Math.random() : rand) * c.length)]
  return { index: i, value: rows[i].value }
}

// Whether `r` would pick a row over the same rows: the Surprise me button is shown only then, so the
// button and the key cannot disagree. Same candidate rule as decideRandomPick; nothing is chosen here.
function canRandomPick(isCandidate, categoryKey, rows, selectedIndex) {
  return candidateIndexes(isCandidate, categoryKey, rows, selectedIndex).length > 0
}

// Categories where `r` never picks, whatever the rows: the image grids with their own keys (walls,
// dotify), the preset and style stage, and the glyph test sweep. Tweak categories are refused by flag.
var REFUSED_CATEGORY = { walls: true, dotify: true, presets: true, styles: true, glyph: true }

// Whether `r` can act on the displayed rows: the category refusal randomPick applies first, then the
// row rule. The Surprise me button, the footer's r hint and randomPick all call this one function, so
// they cannot disagree. Returns false for a refused category even when its rows hold candidates.
function randomAvailable(isCandidate, categoryKey, tweak, rows, selectedIndex) {
  if (tweak === true || REFUSED_CATEGORY[categoryKey] === true) return false
  return canRandomPick(isCandidate, categoryKey, rows, selectedIndex)
}

// The only external command a successful pick produces. The caller executes it:
// Quickshell in the shell, a recording stub in tests.
function applyCommand(scriptPath, categoryKey, value) {
  return [scriptPath, "apply", categoryKey, value]
}
