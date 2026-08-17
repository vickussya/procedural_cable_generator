# Procedural Cable Generator (Blender Add-on)

Simple add-on that creates a cable as a Bezier curve driven by control empties, and can optionally simulate it so
it drapes over and collides with characters and props.

## Background

This tool started as a small workflow script during an environment scene project, to automate repetitive cable setup
and make layout/iteration faster while experimenting with cable routing and dressing.

## Install (classic add-on)

This project is a **classic Blender add-on** and targets **Blender 5.2 LTS**.

The add-on root is the **repository folder itself** (it contains `__init__.py`).

1. Zip the **repo folder** `procedural_cable_generator/` so the zip contains `procedural_cable_generator/__init__.py`.
2. In Blender: `Edit > Preferences > Add-ons > Install...`
3. Select that zip and enable **Procedural Cable Generator**.

## Use

Open the UI here:

`View3D > Sidebar (N) > Cable > Cable Generator`

All creation modes generate a Bezier curve plus control empties in a dedicated collection under `Procedural Cables`.
Moving the `CTRL_*` empties updates the cable shape.

### Create modes

#### 1) From 2 Objects (quick start)

1. Select exactly **two** objects.
2. Make sure the **active** object is the start (last selected).
3. Set **Middle Controls** (0 = straighter, higher = curvier).
4. (Optional) Enable **Parent End Controls** so the start/end controls follow the selected objects.
5. Click **Create Cable From 2 Selected Objects**.

#### 2) From Selected Objects (Chain)

Create a cable that passes through **2+ selected objects** (useful for routing a cable across props).

1. Select **two or more** objects.
2. Set **Chain Order**:
   - **Nearest**: builds a nearest-neighbor chain starting from the active object
   - **Selection**: uses Blender's selection list as-is
   - **Name**: orders by object name
3. (Optional) Enable **Parent Chain Controls** to parent each control to its corresponding selected object.
4. Click **Create Cable From Selected Objects (Chain)**.

Tip: after creating the chain cable, you can freely move the middle `CTRL_*` empties to make the cable messy,
tangled, or to route it around scene geometry.

#### 3) Free Cable (Cursor)

Create a cable with controls only (no object selection required), then move controls by hand to route it anywhere.

1. Place the 3D cursor where you want the cable to start.
2. Set **Free Controls** (total number of control empties) and **Free Length**.
3. Click **Create Free Cable (Cursor)**.

### Legacy mode

If you already have empties named like `OUT_01`, `MID_01`, `IN_01`, you can enable **Show Legacy Tools**
in the panel and run **Create Cables From OUT/MID/IN**.

### Changing a cable after it is created

The **Cable Settings** at the top of the panel apply to *newly created* cables only — they do not retro-edit
existing ones. To change a cable that already exists:

| What you want | Static cable | Dynamic cable |
|---|---|---|
| Thickness | `Object Data > Geometry > Bevel > Depth` | **Appearance > Thickness** |
| Cross-section roundness | `Object Data > Geometry > Bevel > Resolution` | **Appearance > Profile Resolution** |
| Smoothness along its length | `Object Data > Shape > Resolution Preview U` | **Advanced > Divisions Per Segment** |
| Shape | Move the `CTRL_*` empties | Move the `CTRL_*` empties |

On a dynamic cable, *Divisions Per Segment* sets both simulation resolution and rendered smoothness, because the
cable is rebuilt from its simulated points. The Appearance settings also write back to the curve, so a cable keeps
its look if you later remove dynamics.

## Dynamics (Experimental)

Requires **Blender 5.2 LTS**. Any cable created above can be simulated without recreating it.

This is built on Blender 5.2's **Cloth Dynamics (Experimental)** node asset, which Blender itself labels
experimental — its behavior may change in future Blender point releases.

### Quick start

1. Select a cable's curve object (e.g. `CABLE_Cable`).
2. In the panel, open **Dynamics (Experimental)** and click **Make Dynamic**.
3. Go to **frame 1** and press **Play**. The cable is pinned at its `CTRL_*` controls and sags between them under
   gravity — pose the controls by hand, then let physics settle the rest.
4. Tweak the settings live while it plays.
5. **Remove Dynamics** reverts the cable to fully manual/driver-based control at any time.

> Because this is a simulation, **play forward from frame 1** rather than scrubbing. The solver carries state
> between frames, so jumping around the timeline shows partially-solved results.

### Tier: Hero or Background

Set per cable, so a shot can mix a few expensive cables with many cheap ones.

- **Hero** — full cloth simulation with pinning and collision. Use for cables the shot features.
- **Background** — cheap procedural sway: no solver, no collision, held still at both ends. Use for the many
  cables that only need to look alive. Measured at roughly an eighth of Hero's cost.

Background cables have their own *Sway Amount / Speed / Scale / Resolution* settings and ignore the physics and
collision settings entirely. Switching tier is instant and reversible.

### Presets

*Floppy Wire*, *Heavy Cable* and *Frayed Tangle* set thickness, mass, stiffness, bend, damping, friction and
resolution together as a starting point. Editing any of those settings afterwards switches the preset to *Custom*.

Worth knowing: **mass and bend do not change the shape of a cable once it has settled** — a hanging cable's shape
is fixed by its length and span, much as a pendulum's period is independent of its mass. They do change how a cable
reacts to being pushed or dragged, which is where the presets visibly differ.

*Frayed Tangle* currently only supplies parameters; true cable-to-cable tangling needs self-collision, which the
Blender 5.2 node solver does not yet support.

### Attaching controls to a character

1. Select the bone you want in **Pose Mode**, then return to Object Mode. Clicking a bone in the Outliner is not
   enough — Blender does not mark it selected, and the add-on will refuse rather than attach to the wrong thing.
2. Select the `CTRL_*` empties you want to attach.
3. Shift-select the armature (or plain object) **last** so it is active.
4. Click **Attach Controls To Active** under *Attach Controls*. The status bar confirms which bone was used.

The control keeps its current position and then follows the bone or object. Since pinned controls hold exactly,
attaching one to a hand bone makes the cable end track that hand while the rest of the cable simulates.
**Detach Controls** releases them again without moving them.

### Settings

**Appearance** — *Thickness*, *Profile Resolution*. Purely visual; see the table above.

**Physics**

- **Mass** — heavier cables sag more and carry more momentum.
- **Stiffness** — resistance to stretching along the cable's length.
- **Bend Resistance** — resistance to kinking. Low values give floppy wire, high values stiff hose.
- **Damping** — how quickly motion settles. Raise it if a cable keeps swinging.
- **Friction** — how much the cable grips surfaces it slides across.
- **Collision Radius** — the cable's effective thickness for contact, independent of its visual *Thickness*.

**Advanced** — raise with care, as these cost performance.

- **Substeps** / **Constraint Steps** — solver accuracy per frame.
- **Divisions Per Segment** — simulated points between each pair of controls.

### Pin Controls

Decides which `CTRL_*` empties hold the cable while it simulates:

- **All Controls** (default) — every control is pinned, so the cable keeps the pose you set.
- **Ends Only** — only the first and last controls are pinned. Middle controls still shape the cable's rest path,
  but the span between them is free to sag, drape and collide. **Use this for cables interacting with anything.**
- **None** — nothing is pinned and the whole cable falls.

### Collision with characters and props

1. Select the character/prop mesh objects the cable should hit.
2. Click **Add Selected As Colliders**, under *Collision Setup* at the bottom of the panel. This adds a collider
   modifier to each and puts them in a `Cable Colliders` collection, which is assigned to your dynamic cables.
3. Set the cable's **Pin Controls** to *Ends Only* (or *None*) so it has a free span to drape.
4. Go to frame 1 and play — the cable now collides with, drapes over and is pushed by those objects.

The panel warns you if a cable has no colliders assigned, or has every control pinned — the two states in which
collision silently does nothing.

Colliders must be meshes, and are set up as *deforming*, so animated and armature-driven characters work.
Re-running **Add Selected As Colliders** updates existing colliders, so you can use the operator's redo panel
(`F9`) to retune **Margin** and **Friction** — raise Margin if cables sink into thin or fast-moving geometry.

### Don't animate a pinned control into geometry

A pinned control is a **hard constraint**: the cable is forced to that exact point, and collision cannot override
it. Animating a pinned control into a mesh therefore drags the cable straight through it. This is a limitation of
pinning rather than a bug, and no amount of solver tuning avoids it.

To make a cable interact with geometry, do one of these instead:

- **Let it fall.** Set **Pin Controls** to *Ends Only*, place the middle controls above the object, and play from
  frame 1. Gravity drapes the cable onto the mesh — no animation needed. This is the easiest way to test.
- **Animate the character, not the cable.** Set the character up as a collider and animate *it* through the draped
  cable. This is the intended workflow and stays stable even at speed.

### Baking

Three outputs, so you can pick per cable or per shot. All are in the *Bake* box on a Hero cable.

- **Bake Simulation** — fills Blender's native node simulation cache for the scene frame range, so scrubbing is
  fast and the result is stable. **Delete Bake** (trash icon) clears it. The cable still depends on the live setup.
- **Convert To Baked Mesh** — creates a `BAKED_<cable>` mesh with one shape key per frame, animated. Entirely
  self-contained in the `.blend`: it keeps working if you delete the cable, the controls or the colliders. Best for
  locking a shot down. The `.blend` grows with frame count.
- **Export Alembic (.abc)** — writes the evaluated cable out for rendering or handing to another department. The
  **Export Folder** defaults to `//`, meaning the folder holding the current `.blend`, and can be overridden with
  the folder picker. If the `.blend` has not been saved, `//` has nowhere to point, so the export goes to a
  temporary folder and warns you to save first.

All three use the scene's Frame Start/End range.

### Self Collision (optional, heavy)

Blender 5.2's node cloth solver cannot collide a cable with itself, so cables that need to genuinely tangle are
routed through Blender's older Cloth simulation on a hidden proxy object instead. It is **off by default** and
Hero-tier only. Turn it on with **Enable Self Collision**, and tune **Self Distance** — how close the cable may
come to itself before pushing apart.

Two things to know before using it:

- It is **noticeably slower** than the normal solver. Reserve it for the few cables where visible tangling matters.
- The proxy is a flat ribbon, so a slack cable can buckle sideways more than a round cable would, and pinned
  controls are held by a spring rather than exactly. If you need controls pinned precisely, leave self collision
  off.

### Not implemented yet

Nothing outstanding from the original plan. Cloth Dynamics remains experimental in Blender itself, so behavior may
shift in future point releases.

## Repo layout

- `__init__.py` Blender add-on entry point (`bl_info`, register/unregister).
- `operators.py` Operators for creating cables and setting up dynamics/colliders.
- `properties.py` Scene settings, per-cable dynamics settings, and UI properties.
- `panel.py` 3D Viewport sidebar panel.
- `utils.py` Shared utility functions.
- `dynamics.py` Geometry Nodes cloth-dynamics setup for the Dynamics feature.

## License

GPL-3.0. See [LICENSE](LICENSE).
