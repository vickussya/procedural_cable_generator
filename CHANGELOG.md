# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> Note: this project has no prior git tags/releases. The `[1.0.0]` entry below is a retroactive **baseline /
> pre-dynamics snapshot** of the add-on's state on `main` as of 2026-08-14, versioned to match `bl_info["version"]`,
> not an actual tagged release date.

## [Unreleased]

### Added
- **Dynamics (Phase 4): baking and optional self collision.**
  - **Bake Simulation** / **Delete Bake** drive Blender's native node simulation cache.
  - **Convert To Baked Mesh** writes the simulated result into a shape-keyed mesh inside the `.blend`, so it
    survives without the live setup or any external file. It aborts with an error if the cable's vertex count
    changes mid-bake rather than writing a desynchronised result.
  - **Export Alembic (.abc)** writes the evaluated cable out, with an **Export Folder** setting defaulting to `//`
    (beside the `.blend`) and a standard directory picker. An unsaved `.blend` resolves `//` to an empty string, so
    that case falls back to the temp folder and warns to save first instead of failing; the panel warns too.
  - Note: keyframing the Bezier points, as originally sketched, would capture only the control poses — the
    simulated shape lives in the Geometry Nodes output, not the curve points. Hence the mesh and Alembic routes.
  - **Self Collision** (off by default, Hero tier only) routes a cable through a legacy Cloth modifier on a proxy
    object so it can tangle with itself, which the 5.2 node solver cannot do. Enabled and disabled with explicit
    buttons, since toggling it creates or removes an object. Measured findings: legacy Cloth ignores edge-only
    geometry entirely (an edge-only cable fell straight through a floor collider), so the proxy is a faced ribbon
    whose middle row is the cable path; and the ribbon has to be wider than the self-collision distance or its own
    rows inflate it. Limitations, documented in the README: the ribbon behaves like a flat strap so slack cables can
    buckle sideways, and legacy cloth pins with a spring rather than a hard constraint.
- **Dynamics (Phase 3): bone attachment, presets, and performance tiers.**
  - **Attach Controls To Active** / **Detach Controls** (`pcg.attach_control`, `pcg.detach_control`) attach control
    empties to an armature bone or another object, so a cable end can hang from a hand or trail behind a character.
    `utils.parent_keep_world` gained an optional `bone_name`; object parenting is unchanged.
  - **Presets**: *Floppy Wire*, *Heavy Cable*, *Frayed Tangle*, setting thickness, mass, stiffness, bend, damping,
    friction and resolution together. Editing any of those switches the preset to *Custom*. Values were picked
    against measurement: mass and bend do not change the shape of a *settled* hanging cable (that is fixed by its
    length and span), but they clearly change how it responds to being pushed — sweeping a collider through each
    preset displaced the cable 6.42 / 5.19 / 3.06 respectively. *Frayed Tangle* supplies parameters only; genuine
    cable-to-cable tangling needs self-collision, which the 5.2 node solver has no input for.
  - **Hero / Background tiers**, per cable. Hero is the full cloth simulation. Background is cheap noise sway with
    no solver and no collision, tapered to zero at both ends — measured at 0.02 s versus Hero's 0.16 s over 60
    frames. Switching tier swaps the node group in place.
- **Dynamics (Phase 2): collision and pin modes.**
  - `Pin Controls` setting with three modes. **All Controls** (default) keeps Phase 1 behavior, pinning every
    `CTRL_*`. **Ends Only** pins just the first and last control, so middle controls still shape the cable's rest
    path while the span between them is free to drape over and collide with scene geometry. **None** lets the whole
    cable fall.
  - `Collision Collection` setting plus an **Add Selected As Colliders** operator (`pcg.add_selected_colliders`),
    which gives selected mesh objects a collider modifier built from Blender 5.2's bundled `Collider` node asset,
    puts them in a `Cable Colliders` collection, and assigns that collection to the active cable. Colliders are
    marked as deforming, so armature-driven characters are handled.
  - Verified in Blender 5.2: with collision off, a draping cable puts 9 points inside a test box; with collision
    on, 0 points are inside and the cable rests at exactly box top + collision radius.
- `AGENTS.md` rewritten to accurately describe the current repo layout, architecture, conventions, install/test
  steps, and agent operating rules (previous version referenced non-existent `props.py`/`ui.py` files).
- `CHANGELOG.md` added to track changes going forward.
- `AGENTS.md` now documents a testing-strategy convention: new logic (especially upcoming cable dynamics math)
  should be written as plain functions separate from `bpy`/UI glue code, so headless unit tests can be added later
  without a refactor.

### Added
- **Dynamics (Phase 1, Experimental):** new `dynamics.py` module and "Make Dynamic"/"Remove Dynamics" operators
  (`pcg.make_cable_dynamic`, `pcg.remove_cable_dynamics`) let any existing cable curve be simulated with Blender
  5.2's node-based Cloth Dynamics (Experimental) solver, without recreating the cable.
  - Cables are pinned at their existing `CTRL_*` control empties (via a small auxiliary hooked anchor mesh) and
    settle/sag between them under gravity, mass, stiffness, bend, damping, and friction — enabling a "pose by hand,
    then let physics settle" workflow. Pinned controls stay exactly where posed.
  - The simulated result is converted back to curve geometry inside the same node graph, so the cable's existing
    `Thickness`/`Bevel Resolution` settings keep rendering the tube — no separate proxy mesh is rendered and no
    per-frame Python read-back is used live (read-back is reserved for a future explicit bake operator).
  - New per-cable "Dynamics (Experimental)" panel section (`View3D > Sidebar > Cable`) exposing Mass, Stiffness,
    Bend Resistance, Damping, Friction, Collision Radius, Pin Radius, and an Advanced group (Substeps, Constraint
    Steps, Simulation Resolution).
  - `utils.is_cable_curve_object()` helper added to identify add-on-generated cable curves for operator polling.

### Added
- Dynamics: `Add Selected As Colliders` now exposes **Margin**, **Friction** and **Deforming** in its redo panel
  (`F9`), and re-running it updates existing colliders instead of skipping them, so collider settings can be
  retuned without removing and re-adding them. Margin is the collider's surface standoff — raise it if cables
  sink into thin or fast-moving geometry.

### Fixed
- **Dynamics: cables rendered flat with Self Collision enabled.** The cable's path was taken from the cloth
  proxy's middle row using `Mesh to Curve`'s `Selection` input, but that field is evaluated on the *edge* domain,
  so a point-domain mask also matched the ribbon's cross-edges. The resulting curve zig-zagged across the ribbon
  and beveled into a flat strap — measured 0.166 wide against 0.016 tall, where a round tube is 0.016 both ways.
  The outer rows are now deleted before the conversion, giving a clean centreline: the tube measures 0.016 in both
  axes, matching a cable without self collision.
- **Dynamics: attaching a control to a bone silently attached it to the armature object instead.** The operator
  only looked at `Armature.bones.active`, which selecting a bone in the Outliner does not set, and then fell back
  to parenting to the armature object with only a warning. That looks like it worked but never follows the rig's
  bone animation, because an armature object does not move when its bones are posed. Bone selection lives on
  `PoseBone.select` in Blender 5.2 rather than `Bone.select`, so the bone is now resolved from the active pose
  bone, the active bone, or a single selected pose bone — and if no bone can be identified the operator reports an
  error instead of attaching to the object.
- **Dynamics: dynamic cables rendered with no thickness at all.** Blender only applies a curve object's native
  bevel to geometry originating from that object's own curve data, and a dynamic cable is rebuilt from its pin
  anchor object, so the bevel was silently dropped and the cable displayed as a zero-radius line regardless of its
  Thickness. The cable is now beveled inside the node group, and new **Thickness** and **Profile Resolution**
  settings appear under *Appearance* in the Dynamics panel. They adopt the cable's existing bevel when dynamics is
  enabled and write back to it, so switching dynamics on or off no longer changes how thick a cable looks.

- **Dynamics: animating a pinned control dragged the cable through colliders.** A pinned control is a hard
  positional constraint that collision cannot override, so this is inherent rather than a solver bug — measured
  at 11 cable points up to 0.45 m inside a test mesh. The panel warning now says so explicitly, and the README
  documents the two workflows that do work: let the cable fall with *Ends Only* pinning, or animate the collider
  rather than the cable. Draping and animated colliders were measured at zero penetration, including a collider
  crossing 36 m in 60 frames.
- **Dynamics: colliders were set up but never actually used.** Assigning the collider collection to a cable was a
  manual step that was easy to miss, so cables silently passed through colliders that looked correctly configured.
  Now `Add Selected As Colliders` adopts the colliders on any dynamic cable that has no collection chosen yet
  (cables with an explicit choice are left alone), `Make Dynamic` picks up an existing `Cable Colliders` collection
  by default, and the panel warns when a cable has no colliders assigned or has every control pinned — the two
  states in which collision silently does nothing.
- **Dynamics: the "Add Selected As Colliders" button was unreachable.** It sat inside the Dynamics section, which
  only draws when a cable (or one of its controls) is active — but setting up colliders means selecting the
  character/prop meshes, so the button disappeared exactly when it was needed. It now lives in its own
  *Collision Setup* section that is always visible, and the operator reports which collection to assign when no
  cable is active to receive it.
- **Dynamics: controls did not actually hold the cable.** Pin weights were derived from a `Map Range` falloff on
  world-space proximity, which only reaches full strength for a point sitting exactly on a control — so every pin
  was partial. Moving a control 2 m moved the cable only ~0.36 m, kinks appeared at the moved control, and the
  cable eventually sagged away entirely (measured collapse to z=0.18). The simulation is now built from the pin
  anchor polyline and subdivided so controls land on known indices, letting them be pinned at full strength by
  index (`Index % Divisions == 0`). Controls now hold to within a few millimetres, including under repeated
  dragging.
- **Dynamics: the panel section and its operators disappeared while posing.** Both were gated on the *active*
  object being the cable curve, so selecting a `CTRL_*` empty — exactly what you do to pose a cable — hid the
  Dynamics section and disabled its buttons. Added `dynamics.resolve_cable_for_object()`, so the panel and both
  operators now resolve the cable from either the curve or any of its controls.
- **Dynamics: mid-slider Stiffness/Bend values visibly kinked the cable.** These map to XPBD *compliance*, where
  usable cable behavior lives below ~0.06 and ~0.26 already collapses into hard kinks, so the previous linear
  `1 - slider` mapping spent most of its range in unusable territory. Now remapped as `(1 - slider)^3 * 0.1`.
  Worst-case bend across the whole slider range dropped from 161° to 22°.
- `AGENTS.md` rewritten to accurately describe the current repo layout, architecture, conventions, install/test
  steps, and agent operating rules (previous version referenced non-existent `props.py`/`ui.py` files).
- `CHANGELOG.md` added to track changes going forward.
- `AGENTS.md` now documents a testing-strategy convention: new logic (especially upcoming cable dynamics math)
  should be written as plain functions separate from `bpy`/UI glue code, so headless unit tests can be added later
  without a refactor.

### Changed
- `bl_info["blender"]` minimum bumped from `(3, 0, 0)` to `(5, 2, 0)` — the project now targets Blender 5.2 LTS
  only, since upcoming dynamics work depends on 5.2's node-based physics and no backward compatibility is needed.
  `bl_info["version"]` left at `1.0.0` (evaluated and not considered an "early" value worth bumping on its own).
- Dynamics: replaced the `Pin Radius` and `Simulation Resolution` settings with a single `Divisions Per Segment`
  control. Pin Radius no longer has any meaning now that pinning is index-based rather than proximity-based, and
  resolution is derived from the divisions between each pair of controls.
- Dynamics: the generated node group now carries a version marker, so a `.blend` holding a node group from an
  earlier build gets a freshly built one instead of silently reusing an incompatible tree. Cables made dynamic
  with an earlier build should be toggled off and on again (Remove Dynamics → Make Dynamic) to pick it up.
  Bumped again for Phase 2's pin-mode and collision inputs.

## [1.0.0] - 2026-08-14 — baseline / pre-dynamics snapshot

Baseline snapshot of the add-on as found in the repository (see `bl_info` in `__init__.py`), predating any
dynamics/physics work.

### Added
- Classic Blender add-on structure (`__init__.py`, `operators.py`, `properties.py`, `panel.py`, `utils.py`).
- **Create Cable From 2 Selected Objects**: builds a cable between the two selected objects (active = start), with
  configurable middle control count, slack, and optional parenting of end controls to the source objects.
- **Create Cable From Selected Objects (Chain)**: builds a cable through 2+ selected objects, with selectable chain
  ordering (Nearest / Selection / Name) and optional parenting of each control to its source object.
- **Create Free Cable (Cursor)**: builds a cable with only control empties (no object selection required), starting
  at the 3D cursor, with configurable control count and length.
- **Create Cables From OUT/MID/IN** (legacy mode, opt-in via "Show Legacy Tools"): builds cables from existing
  empties named with configurable `OUT_*`/`MID_*`/`IN_*` prefixes.
- Generated cables are organized under a root `Procedural Cables` collection, with one child collection per cable.
- Cable curves stay live-editable: each Bezier point is driven by a scripted driver bound to its `CTRL_*` control
  empty's world-space location, so moving a control empty reshapes the cable immediately.
- 3D Viewport sidebar panel (`View3D > Sidebar (N) > Cable > Cable Generator`) exposing all settings and operators.
- Unique-name handling for generated objects, curves, and collections to avoid collisions.
