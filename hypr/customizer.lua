-- Optional Hyprland hook for the Customizer. Re-applies the saved choices while the config
-- loads, so a `hyprctl reload` never flashes back to the defaults. Without it the Customizer
-- still restores them right after every reload (it listens for `configreloaded`).
--
-- Load it last, e.g. at the end of ~/.config/hypr/looknfeel.lua:
--   dofile(os.getenv("HOME") .. "/.config/omarchy/plugins/kamradsmeshnyavy.customizer/hypr/customizer.lua")

local home = os.getenv("HOME")
local state = os.getenv("XDG_STATE_HOME") or (home .. "/.local/state")
local plugin = home .. "/.config/omarchy/plugins/kamradsmeshnyavy.customizer"

local function read_line(path)
	local f = io.open(path, "r")
	local line = f and f:read("*l")
	if f then
		f:close()
	end
	return line
end

local function exists(path)
	local f = path and io.open(path, "r")
	if f then
		f:close()
	end
	return f ~= nil
end

-- "<name> <numbers…>" saved by scripts/opacity.sh and scripts/blur.sh.
local function values(name)
	local out = {}
	for n in (read_line(state .. "/hypr/" .. name) or ""):gmatch("%s([%d.]+)") do
		out[#out + 1] = tonumber(n)
	end
	return out
end

-- Screen shader + the damage_tracking it needs: "<path> <damage_tracking>" (scripts/crt-toggle.sh).
do
	local path, dt = (read_line(state .. "/hypr/screen-shader") or ""):match("^(%S+)%s+(%d)$")
	if path and not exists(path) then
		-- Saved by an older layout: find the shader by name.
		local name = path:match("([^/]+)%.frag$") or ""
		for _, dir in ipairs({ home .. "/.config/omarchy/customizer/shaders", plugin .. "/shaders" }) do
			if exists(dir .. "/" .. name .. ".frag") then
				path = dir .. "/" .. name .. ".frag"
				break
			end
		end
	end
	if path and exists(path) then
		hl.config({ decoration = { screen_shader = path }, debug = { damage_tracking = tonumber(dt) } })
	end
end

do
	local o = values("opacity")
	if #o == 2 then
		hl.config({ decoration = { active_opacity = o[1], inactive_opacity = o[2] } })
	end

	local b = values("blur")
	if #b == 4 then
		hl.config({
			decoration = {
				blur = {
					enabled = b[1] > 0,
					size = math.max(1, b[1]),
					passes = b[2],
					vibrancy = b[3],
					noise = b[4],
				},
			},
		})
	end

	-- Optional window geometry override saved by presets ("<name> <gaps_in> <gaps_out> <border_size> <rounding> <shadow_0_or_1>").
	-- Omarchy's "no gaps" toggle (Super+Shift+Backspace) wins while it is on.
	local g = values("geometry")
	local no_gaps = exists(state .. "/omarchy/toggles/hypr/window-no-gaps.lua")
	if #g == 5 and not no_gaps then
		hl.config({
			general = {
				gaps_in = g[1],
				gaps_out = g[2],
				border_size = g[3],
			},
			decoration = {
				rounding = g[4],
				shadow = { enabled = g[5] > 0 },
			},
		})
	end
end

-- Windows tab (Customizer → Windows, ~/.config/omarchy/customizer/windows.json): gaps, border, rounding,
-- shadow, dim, layout. Only the keys present there are applied, on top of the style geometry above;
-- Omarchy's "no gaps" toggle still wins for gaps / border / rounding.
do
	local f = io.open(home .. "/.config/omarchy/customizer/windows.json", "r")
	local json = f and f:read("*a") or ""
	if f then
		f:close()
	end
	local function num(key)
		return tonumber(json:match('"' .. key .. '"%s*:%s*(%-?[%d.]+)'))
	end
	local function bool(key)
		local v = json:match('"' .. key .. '"%s*:%s*(%a+)')
		if v == nil then
			return nil
		end
		return v == "true"
	end
	local no_gaps = exists(state .. "/omarchy/toggles/hypr/window-no-gaps.lua")
	local general, decoration = {}, {}
	if not no_gaps then
		general.gaps_in = num("windowGapsIn")
		general.gaps_out = num("windowGapsOut")
		general.border_size = num("windowBorder")
		decoration.rounding = num("windowDecoRounding")
	end
	local layout = json:match('"windowLayout"%s*:%s*"(%a+)"')
	if layout == "dwindle" or layout == "master" then
		general.layout = layout
	end
	local shadow, range = bool("windowShadow"), num("windowShadowRange")
	if shadow ~= nil or range ~= nil then
		decoration.shadow = { enabled = shadow, range = range }
	end
	decoration.dim_inactive = bool("windowDim")
	decoration.dim_strength = num("windowDimStrength")
	hl.config({ general = general, decoration = decoration })
end

-- Window corners (Customizer → Windows → Window corners, ~/.config/omarchy/customizer/windows.json).
-- A window rule, not decoration.rounding: rules beat the global value and Omarchy's "no gaps"
-- toggle, and tiled windows can stay square so the grid stays seamless (the bar's screen frame
-- already rounds their outer corners). "float" = floating and popped windows, "all", "off".
do
	local f = io.open(home .. "/.config/omarchy/customizer/windows.json", "r")
	local json = f and f:read("*a") or ""
	if f then
		f:close()
	end
	local mode = json:match('"windowRounding"%s*:%s*"(%a+)"') or "float"
	local radius = tonumber(json:match('"windowRadius"%s*:%s*([%d.]+)')) or 16
	local power = tonumber(json:match('"windowRoundingPower"%s*:%s*([%d.]+)')) or 2.5
	if mode ~= "off" then
		hl.config({ decoration = { rounding_power = power } })
		if mode == "all" then
			hl.window_rule({ match = { class = ".*" }, rounding = radius })
		else
			hl.window_rule({ match = { float = true }, rounding = radius })
		end
	end
end

-- The animation preset picked in the Customizer.
local anims = state .. "/omarchy-customizer/animations.lua"
if exists(anims) then
	dofile(anims)
end

-- Blur behind the Customizer overlay itself.
hl.layer_rule({ match = { namespace = "omarchy-customizer" }, blur = true, ignore_alpha = 0.6 })
