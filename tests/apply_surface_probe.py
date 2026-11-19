"""Probe for ui/ApplyFlow.js: runs apply_ops.apply() for every row the backend lists and reports
which calls could open a surface (a zenity dialog, a terminal, the lock preview, the launcher, a
picker, or a change of the loaded plugins).

Everything runs in a temp HOME; subprocess and the named surface helpers are replaced with
recorders, so nothing reaches the real desktop. Prints one JSON document on stdout:
  {"results": [{category, value, surface, surfaces, calls, error}], "skipped": N, "categories": {...}}
tests/test_apply_flow.cjs compares each result with ApplyFlow.keepsOpen.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# paths reads HOME and XDG_* at import time, so the sandbox must exist before the backend loads.
SANDBOX = tempfile.mkdtemp(prefix="apply-surface-probe-")
HOME = os.path.join(SANDBOX, "home")
os.makedirs(HOME)
os.environ["HOME"] = HOME
for _name in ("XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
    os.environ[_name] = os.path.join(SANDBOX, _name.lower())
sys.path.insert(0, os.path.join(PLUGIN, "backend"))

from customizer import apply_ops, lists, paths, preview_ops, state  # noqa: E402

if not str(paths.HOME).startswith(SANDBOX):
    sys.exit("probe refuses to run: paths.HOME is outside the sandbox")

calls = []      # argv of every subprocess and spawn call made by one apply
surfaces = []  # named surface helpers called by one apply


def argv_opens_surface(argv):
    """True when a plain command line opens a dialog, terminal, lock preview, launcher or changes plugins."""
    if not argv:
        return False
    head = os.path.basename(str(argv[0]))
    rest = [str(a) for a in argv[1:]]
    if head == "zenity":
        return True
    if head.startswith("omarchy-launch-"):
        return True
    if head == "omarchy-shell" and any(a in ("lock", "launcher") for a in rest):
        return True
    if head == "omarchy" and "plugin" in rest and ("enable" in rest or "disable" in rest):
        return True
    return False


def record(args):
    argv = [str(a) for a in args] if isinstance(args, (list, tuple)) else [str(args)]
    calls.append(argv)
    return argv


def fake_run(args, *a, **kw):
    argv = record(args)
    # zenity cancels: the apply takes its cancel path.
    code = 1 if argv and os.path.basename(argv[0]) == "zenity" else 0
    return subprocess.CompletedProcess(argv, code, stdout="", stderr="")


def fake_check(args, *a, **kw):
    record(args)
    return ""


class FakePopen:
    """Minimal Popen stand-in: records argv and reports a finished, successful process."""

    def __init__(self, args, *a, **kw):
        self.args = args
        self.pid = 0
        self.returncode = 0
        record(args)

    def wait(self, timeout=None):
        return 0

    def poll(self):
        return 0

    def communicate(self, input=None, timeout=None):
        return ("", "")

    def kill(self):
        pass

    def terminate(self):
        pass


def fake_sh(args, env=None, quiet=True):
    """Replaces apply_ops.sh and preview_ops.sh (the same function in the backend)."""
    argv = record(args)
    code = 1 if argv and os.path.basename(argv[0]) == "zenity" else 0
    return (code, "")


def fake_spawn(args, *a, **kw):
    record(args)


def mark(label, ret=None, cancel=False):
    """Recorder for a named surface helper: records the surface, then returns `ret` or, when `cancel`,
    behaves like a cancelled picker (apply_ops turns that into Exit(0))."""
    def fn(*a, **kw):
        surfaces.append(label)
        if cancel:
            raise apply_ops.Exit(0)
        return ret
    return fn


def install_fakes():
    subprocess.run = fake_run
    subprocess.Popen = FakePopen
    subprocess.call = fake_check
    subprocess.check_call = fake_check
    subprocess.check_output = fake_check
    apply_ops.sh = fake_sh
    preview_ops.sh = fake_sh
    apply_ops.spawn = fake_spawn
    # Named surface helpers: a surface even when the command line is not visible here.
    apply_ops._zenity = mark("_zenity")
    apply_ops.tweak_pick = mark("tweak_pick")
    apply_ops.save_user_preset = mark("save_user_preset")
    apply_ops.save_user_style = mark("save_user_style")
    apply_ops.save_user_skin = mark("save_user_skin")
    apply_ops.save_user_layout = mark("save_user_layout")
    apply_ops.lock_thumbs = mark("lock_thumbs")
    apply_ops._pick_images = mark("_pick_images", cancel=True)
    apply_ops._pick_dir = mark("_pick_dir", cancel=True)
    preview_ops.launcher_open = mark("launcher_open")
    # tweak_ops.tweak opens a zenity picker for pick-kind rows; kind is not known here, so every call counts.
    from customizer import tweak_ops
    tweak_ops.tweak = mark("tweak_ops.tweak")


def row_value(row):
    """Value column of a listed row (tab-separated, value at index 1), or "" when absent."""
    parts = str(row).split("\t")
    return parts[1] if len(parts) > 1 else ""


def is_applied_row(value):
    """Headers and directory-navigation rows are not applied by the UI."""
    return value != "" and not value.startswith("section:") and not value.startswith("dir:")


def categories():
    return sorted(set(list(lists.LISTS) + ["theme-walls"]))


def seed_sandbox():
    """One user theme and one lock design, so the themes and lock listings have rows to apply.

    themes lists the directories under the config themes dir; lock reads designs/designs.json from the
    lock plugin directory. Both live under the temp HOME, so the probe never sees the host's themes.
    """
    theme_dir = os.path.join(str(paths.CONFIG), "themes", "probe-theme")
    os.makedirs(theme_dir, exist_ok=True)
    # Backend modules write under these without creating them (animation backup, runtime state).
    os.makedirs(str(paths.STATE), exist_ok=True)
    os.makedirs(str(paths.RUN), exist_ok=True)
    designs_dir = os.path.join(str(state.LOCK_PLUGIN), "designs")
    os.makedirs(designs_dir, exist_ok=True)
    with open(os.path.join(designs_dir, "designs.json"), "w", encoding="utf-8") as fh:
        json.dump([{"id": "probe-design", "name": "Probe design"}], fh)


def main():
    seed_sandbox()
    # Listing reads the sandbox and the host tools it calls, so it runs before the fakes replace
    # subprocess; applying the rows afterwards cannot change what was listed.
    listed = {}
    errors = {}
    for category in categories():
        try:
            listed[category] = lists.list_category(category) or []
        except Exception as exc:  # a listing that cannot run in the sandbox is reported, not fatal
            errors[category] = f"{type(exc).__name__}: {exc}"
    install_fakes()
    results = []
    counts = {}
    skipped = 0
    for category, items in listed.items():
        for row in items:
            value = row_value(row)
            if not is_applied_row(value):
                skipped += 1
                continue
            del calls[:]
            del surfaces[:]
            error = None
            try:
                apply_ops.apply(category, value)
            except apply_ops.Exit as exc:
                error = f"Exit({exc.code})"
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            surface = bool(surfaces) or any(argv_opens_surface(c) for c in calls)
            counts[category] = counts.get(category, 0) + 1
            results.append({
                "category": category,
                "value": value,
                "surface": surface,
                "surfaces": list(surfaces),
                "calls": [c for c in calls],
                "error": error,
            })
    print(json.dumps({"results": results, "skipped": skipped, "categories": counts, "errors": errors}))


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(SANDBOX, ignore_errors=True)
