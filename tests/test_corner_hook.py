#!/usr/bin/python3 -I
"""Window corners (windows.json) in hypr/customizer.lua, the Python restore and the bash mirror.

  /usr/bin/python3 -I tests/test_corner_hook.py

Needs lua5.4. The hook runs under lua5.4 with a stub `hl` (Hyprland's Lua API) that prints every call, so the test
reads what the hook would send. The same windows.json is then restored through backend/run.py and through the bash
mirror (tests/legacy/customizer.sh restore); their corner evals must match exactly. Each case: a windows.json (or
none), the saved power, the rule kind (None / "float" / "all") and the radius the rule carries.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
HOOK = os.path.join(PLUGIN, "hypr/customizer.lua")
LEGACY = os.path.join(PLUGIN, "tests/legacy/customizer.sh")
sys.path.insert(0, HERE)
import test_new_commands as tn  # noqa: E402  (sandbox, run and calls: the same stubs as the other restore cases)

# Serialises each hl.* argument with sorted keys: `hl.window_rule {match={float=true},rounding=12}`.
STUB = r'''
local function ser(v)
  if type(v) == "string" then return '"' .. v .. '"' end
  if type(v) ~= "table" then return tostring(v) end
  local keys = {}
  for k in pairs(v) do keys[#keys + 1] = k end
  table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
  local parts = {}
  for _, k in ipairs(keys) do parts[#parts + 1] = tostring(k) .. "=" .. ser(v[k]) end
  return "{" .. table.concat(parts, ",") .. "}"
end
hl = setmetatable({}, { __index = function(_, name)
  return function(arg) print(name .. " " .. ser(arg)) end
end })
dofile(arg[1])
'''

# (windows.json or None for no file, saved power, rule kind, radius)
CASES = [
    (None, None, None, None),
    ({}, None, None, None),
    ({"windowGapsIn": 6}, None, None, None),
    ({"windowRoundingPower": 3}, "3", None, None),
    ({"windowRoundingPower": 3, "windowRounding": "off"}, None, None, None),
    ({"windowRadius": 12}, None, "float", "12"),
    ({"windowRounding": "float", "windowRadius": 8, "windowRoundingPower": 2.5}, "2.5", "float", "8"),
    ({"windowRounding": "all", "windowRadius": 8}, None, "all", "8"),
    ({"windowRounding": "all", "windowRadius": 8, "windowRoundingPower": 2.5}, "2.5", "all", "8"),
    ({"windowRounding": "off", "windowRadius": 8}, None, None, None),
]


def write_cfg(home, payload):
    cfg = os.path.join(home, ".config/omarchy/customizer/windows.json")
    os.makedirs(os.path.dirname(cfg), exist_ok=True)
    if payload is None:
        if os.path.exists(cfg):
            os.unlink(cfg)
    else:
        with open(cfg, "w") as f:
            json.dump(payload, f)


def hook_out(payload):
    """Runs the hook once under lua5.4 in a fresh HOME; returns (rc, stderr, printed lines)."""
    base = tempfile.mkdtemp(prefix="corner-hook.", dir=os.environ.get("XDG_RUNTIME_DIR") or None)
    home, stub = os.path.join(base, "home"), os.path.join(base, "stub.lua")
    write_cfg(home, payload)
    with open(stub, "w") as f:
        f.write(STUB)
    env = {"HOME": home, "XDG_STATE_HOME": os.path.join(base, "state"), "PATH": os.environ["PATH"]}
    r = subprocess.run(["lua5.4", stub, HOOK], env=env, capture_output=True, text=True)
    return r.returncode, r.stderr, r.stdout.splitlines()


def hook_ok(payload, power, rule, radius):
    rc, err, out = hook_out(payload)
    power_lines = [l for l in out if "rounding_power" in l]
    rules = [l for l in out if l.startswith("window_rule ")]
    want_power = [] if power is None else [f"rounding_power={power}}}"]
    want_rules = [] if rule is None else [
        'window_rule {match={' + ('class=".*"' if rule == "all" else "float=true") + "},rounding=" + radius + "}"]
    power_ok = len(power_lines) == len(want_power) and all(w in power_lines[0] for w in want_power)
    return rc == 0 and not err.strip() and power_ok and rules == want_rules, (rc, err.strip(), power_lines, rules)


def corner_evals(calls_before, log):
    return [c for c in tn.calls(log)[calls_before:] if "rounding_power" in c or "window_rule" in c]


def main():
    fails = []

    def check(name, cond, detail=""):
        print(("ok    " if cond else "FAIL  ") + name + ("" if cond else f"  {detail}"))
        if not cond:
            fails.append(name)

    try:
        subprocess.run(["lua5.4", "-v"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        print("FAIL  lua5.4 is required to run hypr/customizer.lua")
        return 1

    # ── 1. The hook, run as Hyprland runs it ──
    for payload, power, rule, radius in CASES:
        ok, detail = hook_ok(payload, power, rule, radius)
        check(f"hook {json.dumps(payload)}: power {power}, rule {rule} r={radius}", ok, detail)

    # ── 2. Python restore and bash mirror: the same corner evals for the same windows.json ──
    base, home, log, env = tn.sandbox()
    state = os.path.join(base, "state")
    os.makedirs(os.path.join(state, "hypr"))  # crt-toggle.sh needs the state directory
    wenv = dict(env, XDG_STATE_HOME=state)
    for payload, power, rule, radius in CASES:
        write_cfg(home, payload)
        n = len(tn.calls(log))
        tn.run(wenv, "restore")
        py = corner_evals(n, log)
        n = len(tn.calls(log))
        subprocess.run(["bash", LEGACY, "restore"], env=wenv, capture_output=True, text=True)
        sh = corner_evals(n, log)
        label = f"{json.dumps(payload)}"
        check(f"restore {label}: bash mirror emits the same corner evals as Python", py == sh, f"py={py} sh={sh}")
        want_power = [] if power is None else [f"rounding_power = {power}"]
        match = "{ class = \".*\" }" if rule == "all" else "{ float = true }"
        want_rules = [] if rule is None else [f"hl.window_rule({{ match = {match}, rounding = {radius} }})"]
        got_power = [c for c in py if "rounding_power" in c]
        got_rules = [c for c in py if "hl.window_rule" in c]
        check(f"restore {label}: python power {want_power or 'none'}",
              all(w in got_power[0] for w in want_power) if want_power else not got_power, f"{py}")
        check(f"restore {label}: python rule {want_rules or 'none'}",
              all(w in got_rules[0] for w in want_rules) if want_rules else not got_rules, f"{py}")

    print(f"{'OK' if not fails else 'FAIL'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
