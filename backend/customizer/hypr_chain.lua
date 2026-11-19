-- Effective Hyprland option values for the Windows tab, read the way Hyprland loads its Lua config.
-- Usage: lua5.4 hypr_chain.lua <entry.lua> <option path>...   (e.g. general.gaps_in)
-- Runs the entry config (hyprland.lua, which pulls in Omarchy's defaults and the user's files)
-- with hl.config recorded instead of applied: later hl.config calls override earlier ones, as in
-- Hyprland, and hl.get_config reads what the chain has set so far. Compositor-only calls (binds,
-- rules, events, windows, workspaces) are no-ops, and the load is read-only: file writes and
-- shell commands do not run (only `find`, which require_all uses to list directories).
-- A module that fails under these stubs, or runs out of its step budget, is skipped with a note on
-- stderr and the rest of the chain still loads. Prints "<option path>\t<value>" for each requested
-- option the chain sets to a number, boolean or string; unset options print nothing.
-- Exits 1 when the entry itself fails to load.
-- Called from hypr_defaults.py; see tests/test_displayed_values.py.

local entry = arg[1]
local effective = {}

local function merge(dst, src)
  for k, v in pairs(src) do
    if type(v) == "table" then
      if type(dst[k]) ~= "table" then dst[k] = {} end
      merge(dst[k], v)
    else
      dst[k] = v
    end
  end
end

local function lookup(path)
  local node = effective
  for part in path:gmatch("[^.]+") do
    if type(node) ~= "table" then return nil end
    node = node[part]
  end
  return node
end

-- Any other hl.* / o.* call returns this sink. Only string keys chain: integer indexes stay nil,
-- so loops over a sink (ipairs) end at once instead of spinning.
local sink
sink = setmetatable({}, {
  __index = function(_, k) if type(k) == "string" then return sink end end,
  __call = function() return sink end,
})

hl = setmetatable({
  config = function(opts) if type(opts) == "table" then merge(effective, opts) end end,
  get_config = function(path) return lookup(path) end,
  get_windows = function() return {} end,
}, { __index = function(_, k) if type(k) == "string" then return sink end end })

local real_open, real_popen = io.open, io.popen
io.open = function(path, mode)
  if mode and mode:find("[wa+]") then return nil end
  return real_open(path, mode)
end
io.popen = function(cmd, mode)
  if cmd:match("^find ") then return real_popen(cmd, mode) end
  return nil
end
os.execute = function() return nil end

-- Step budget per top-level load (hook every 1000 VM instructions). Runaway code under the stubs
-- hits it and is skipped; nested requires share the budget of the load that started them.
local BUDGET = 20000
local depth, steps = 0, 0
local function guarded(fn, ...)
  if depth == 0 then
    steps = 0
    debug.sethook(function()
      steps = steps + 1
      if steps > BUDGET then error("step budget exceeded", 0) end
    end, "", 1000)
  end
  depth = depth + 1
  local ok, res = pcall(fn, ...)
  depth = depth - 1
  if depth == 0 then debug.sethook() end
  return ok, res
end

local real_require = require
require = function(name)
  local ok, res = guarded(real_require, name)
  if ok then return res end
  io.stderr:write("skipped ", name, ": ", tostring(res), "\n")
  return sink
end

local ok, err = guarded(dofile, entry)
if not ok then
  io.stderr:write(tostring(err), "\n")
  os.exit(1)
end

for i = 2, #arg do
  local node = lookup(arg[i])
  local t = type(node)
  if t == "number" or t == "boolean" or t == "string" then
    print(arg[i] .. "\t" .. tostring(node))
  end
end
