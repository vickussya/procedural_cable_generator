# AGENTS.md

Instructions for AI agents (and human contributors) working in this repository. Read this before making changes.

## Project overview

**Procedural Cable Generator** is a classic Blender add-on that generates editable cables as Bezier curves driven by
control empties (`CTRL_*`). Moving a control empty updates the cable shape live via drivers — no modifier stack or
simulation is involved. It started as a workflow script for automating cable layout/dressing in environment scenes.

- Target: **Blender 5.2 LTS only** (`bl_info["blender"] = (5, 2, 0)`). No backward compatibility with earlier
  Blender versions is required — upcoming dynamics work depends on 5.2's node-based physics.
- License: **GPL-3.0** (see `LICENSE`).
- Current version per `bl_info`: **1.0.0**.

The add-on is a **classic add-on** (not an Extension/manifest-based add-on): the repository root itself is the add-on
package and contains `__init__.py` directly.

## Repository layout

| File | Responsibility |
|---|---|
| `__init__.py` | Add-on entry point. Defines `bl_info`, the `_CLASSES` registration tuple, and `register()`/`unregister()`. |
| `operators.py` | All `bpy.types.Operator` subclasses that create cables (the four creation modes described below). |
| `properties.py` | `PCG_Settings`, the `PropertyGroup` holding all scene-level UI/tool settings (attached to `Scene.pcg_settings`). |
| `panel.py` | `PCG_PT_cable_panel`, the single 3D Viewport sidebar (N-panel) UI under `View3D > Sidebar > Cable`. |
| `utils.py` | Shared helpers: collection management, unique naming, empty creation, parenting, driver wiring, and curve construction. No Blender operator/UI classes live here. |
| `README.md` | User-facing install and usage instructions. |
| `LICENSE` | GPL-3.0 license text. |
| `.gitignore` | Standard Blender/Python/VS Code ignores. |

There is no test suite, no build tooling, and no external dependencies beyond `bpy`/`mathutils` (Blender's bundled API).

## Architecture & conventions

**Registration pattern** (`__init__.py`):
- All registerable classes live in the `_CLASSES` tuple, in dependency order — `PCG_Settings` (the `PropertyGroup`)
  is registered first since `Scene.pcg_settings` depends on it.
- `register()` iterates `_CLASSES` forward and then attaches `bpy.types.Scene.pcg_settings = PointerProperty(...)`.
- `unregister()` removes `Scene.pcg_settings` first, then iterates `_CLASSES` in **reverse** to avoid dependency
  issues. Any new registerable class must be added to `_CLASSES`, not registered ad hoc.

**Naming conventions:**
- Operator classes: `PCG_OT_<verb_description>`, `bl_idname = "pcg.<snake_case_action>"`.
- Panel class: `PCG_PT_<name>`.
- Property group: `PCG_Settings`.
- Generated control empties: `CTRL_<cable_name>_START` / `_END` / `_MID_<NN>`, made unique via `utils.unique_name()`.
- Generated curve object/data: `CABLE_<cable_name>`.
- Root collection: `"Procedural Cables"` (`utils.ROOT_COLLECTION_NAME`), holding one child collection per cable named
  `Cable_<cable_name>`.
- Legacy mode (opt-in via "Show Legacy Tools"): matches pre-existing empties by configurable prefixes, default
  `OUT_*` / `MID_*` (optional) / `IN_*`, and creates cables from them without generating new control empties.

**How things are wired:**
- Operators read/write settings via `context.scene.pcg_settings` (a `PCG_Settings` instance).
- `panel.py` draws `PCG_PT_cable_panel`, one UI section per operator, reading/writing the same `pcg_settings`.
- Cable creation always goes through `utils.create_cable_curve()`, which builds a Bezier spline with `AUTO` handles
  and — critically — binds each Bezier point's `co` to its corresponding control empty via a **scripted driver**
  (`utils.add_point_world_location_driver`), reading the empty's world-space `LOC_X/Y/Z`. This driver is what makes
  moving a `CTRL_*` empty update the curve live, independent of parenting.
- Parenting (`utils.parent_keep_world`) is separate and optional — it's used so control empties can *follow* a
  source object's transform (e.g. "Parent End Controls"), while the driver is what makes the *curve* follow the
  *empty*.
- Collections are always created/found via `utils.ensure_root_collection()` / `utils.new_child_collection()`, never
  by touching `bpy.data.collections` directly in operator code.

**Code style to match:**
- Type-hinted function signatures (`context: bpy.types.Context`, `-> list[bpy.types.Object]`, etc.).
- Keyword-only arguments (`*, ...`) for helpers with several parameters.
- Small, focused helpers in `utils.py` rather than duplicated logic in operators.
- Operators use `bl_options = {"REGISTER", "UNDO"}`, implement `poll()` where creation preconditions exist, and use
  `self.report({"ERROR"|"WARNING"|"INFO"}, ...)` for user feedback rather than raising exceptions.
- Minimal inline comments — only where Blender behavior is non-obvious (see the comment on `driver.variables` in
  `utils.py` for the expected tone/density).
- Artist-friendly, concise UI labels and tooltips.

## How to install & test

1. **Install:** Zip this repository's folder so the zip's top-level entry is `procedural_cable_generator/` containing
   `__init__.py` directly (i.e. the folder you zip must be named `procedural_cable_generator`). In Blender:
   `Edit > Preferences > Add-ons > Install...`, select the zip, enable **Procedural Cable Generator**.
2. **Open the UI:** `View3D > Sidebar (N) > Cable > Cable Generator`.
3. **Smoke-test each creation mode after any change:**
   - **From 2 Objects:** select exactly two objects (active = start), set Middle Controls, optionally enable Parent
     End Controls, click **Create Cable From 2 Selected Objects**. Verify a curve + `CTRL_*` empties appear under
     `Procedural Cables`, and moving a `CTRL_*` empty updates the curve shape.
   - **From Selected Objects (Chain):** select 2+ objects, try each Chain Order (Nearest/Selection/Name), optionally
     enable Parent Chain Controls, click **Create Cable From Selected Objects (Chain)**. Verify ordering and that
     controls are parented when the option is on.
   - **Free Cable (Cursor):** position the 3D cursor, set Free Controls/Free Length, click **Create Free Cable
     (Cursor)**. Verify the cable is created at the cursor with the requested control count.
   - **Legacy (OUT/MID/IN):** enable "Show Legacy Tools", ensure objects named with the configured prefixes exist,
     click **Create Cables From OUT/MID/IN**. Verify matching by suffix works and unmatched `OUT_*` objects are
     skipped without crashing.
   - Also verify `unregister()`/`register()` round-trips cleanly (disable/re-enable the add-on) with no errors in
     the Blender console.

**Testing strategy convention:** there is no automated test suite today, and manual in-Blender smoke testing (above)
remains the only requirement for now. However, new non-trivial logic (especially cable/dynamics math: sag, easing,
constraint solving, etc.) should be written as plain functions operating on `mathutils.Vector`/numbers rather than
reaching into `bpy.data`/`bpy.context` directly, and kept separate from the `bpy.types.Operator`/`Panel` glue code
that calls them (following the existing `utils.py` split). This costs nothing today but means headless unit tests
can be added later without a refactor.

## Agent operating rules

- **Scope-limited:** only read/create/modify files inside this repository. Never touch files elsewhere on the
  system, global config, or other projects. No commands that reach outside the repo.
- **No unrequested dependencies:** don't install packages, add dependencies, or fetch remote resources without
  asking first and explaining why.
- **Non-destructive & additive:** never delete or overwrite existing files/code without showing the change and
  getting explicit approval first. Prefer additive changes; when modifying existing code, make the smallest change
  that works and preserve current behavior and all public operator IDs (`bl_idname`s).
- **No unrelated cleanup:** never rewrite a whole file when a targeted edit will do; no mass reformatting or
  unrelated "cleanup"; don't remove comments, license headers, or existing functionality as a side effect.
- **Preserve working functionality:** all four existing creation modes must keep working after every change. If
  unsure whether something is used, ask — don't assume it's dead code.
- **Git hygiene:** don't rewrite history, force-push, discard changes, or check out over uncommitted work. Never
  `git add`/`commit`/`push` unless explicitly asked. Leave the working tree clean and non-broken after every step.
- **Communicate in small steps:** explain what's about to change and why before changing it; ask clarifying
  questions before writing code when a request is ambiguous; flag assumptions about the Blender 5.2 API rather than
  guessing, and verify against the installed Blender where possible.
- **Changelog discipline:** every change gets a bullet in `CHANGELOG.md` under `[Unreleased]` (see that file).

## Definition of done

A change is done when:
1. All existing creation modes (From 2 Objects, Chain, Free Cable, Legacy OUT/MID/IN) still work as before, unless
   the task explicitly changes one of them (and that's called out).
2. `CHANGELOG.md` has a new bullet under `[Unreleased]`, in the correct category, describing what changed and why.
3. The working tree is left in a clean, non-broken state (no partial edits, no stray debug code).

## Open questions

- None currently. Prior questions were resolved 2026-08-14: `bl_info["blender"]` is pinned to `(5, 2, 0)` with no
  back-compat requirement; automated testing stays manual for now, with the "Testing strategy convention" above as
  the guardrail for future dynamics code; the `CHANGELOG.md` baseline entry is explicitly labeled as a retroactive
  pre-dynamics snapshot rather than a real tagged release.
