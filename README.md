# Procedural Cable Generator (Blender Add-on)

Simple add-on that creates a cable as a Bezier curve driven by control empties.

<img width="322" height="429" alt="Screenshot 2026-04-20 134153" src="https://github.com/user-attachments/assets/fea7951d-719d-423c-b125-5c7ed3339925" />

## Background

This tool started as a small workflow script during an environment scene project, to automate repetitive cable setup
and make layout/iteration faster while experimenting with cable routing and dressing.

## Install (classic add-on)

This project is a **classic Blender add-on**.

The add-on root is the **repository folder itself** (it contains `__init__.py`).

1. Zip the **repo folder** `procedural_cable_generator/` so the zip contains `procedural_cable_generator/__init__.py`.
2. In Blender: `Edit > Preferences > Add-ons > Install...`
3. Select that zip and enable **Procedural Cable Generator**.

## Use (v1)

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

## Legacy mode

If you already have empties named like `OUT_01`, `MID_01`, `IN_01`, you can enable **Show Legacy Tools**
in the panel and run **Create Cables From OUT/MID/IN**.

## Dynamics (Experimental, work in progress)

Requires **Blender 5.2 LTS**. Any cable created above can be simulated without recreating it:

1. Select a cable's curve object (e.g. `CABLE_Cable`).
2. In the panel, open **Dynamics (Experimental)** and click **Make Dynamic**.
3. Scrub or play the timeline. The cable is pinned exactly at its `CTRL_*` controls and sags/settles between them
   under gravity — pose the controls by hand first, then let physics settle the rest.
4. Tweak Mass / Stiffness / Bend Resistance / Damping / Friction / Collision Radius live.
5. **Remove Dynamics** reverts the cable to fully manual/driver-based control at any time.

### Pin Controls

`Pin Controls` decides which `CTRL_*` empties hold the cable while it simulates:

- **All Controls** (default) — every control is pinned, so the cable keeps the pose you set.
- **Ends Only** — only the first and last controls are pinned. The middle controls still shape the cable's rest
  path, but the span between them is free to sag, drape and collide. Use this for cables hanging over characters
  or props.
- **None** — nothing is pinned and the whole cable falls.

### Collision with characters and props

1. Select the character/prop mesh objects the cable should hit.
2. Click **Add Selected As Colliders**, under *Collision Setup* at the bottom of the panel. This adds a collider
   modifier to each and puts them in a `Cable Colliders` collection.
3. Select the cable and set its **Collision Collection** to `Cable Colliders`.
   (Tip: if you select the collider meshes *and* the cable, with the cable active, step 3 happens automatically.)
4. Set the cable's **Pin Controls** to *Ends Only* (or *None*) so it has a free span to drape.
5. Play the timeline — the cable now collides with, drapes over and is pushed by those objects.

Colliders are set up as *deforming*, so animated/armature-driven characters work. Collider objects must be
meshes. **Collision Radius** controls the cable's effective thickness for contact, independent of its visual
`Thickness`. Re-running **Add Selected As Colliders** updates existing colliders, so you can use the operator's
redo panel (`F9`) to retune **Margin** and **Friction** — raise Margin if cables sink into thin or fast-moving
geometry.

### Don't animate a pinned control into geometry

A pinned control is a **hard constraint**: the cable is forced to that exact point. Collision cannot override it,
so animating a pinned control into a mesh drags the cable straight through. This is a limitation of pinning, not
a bug — measured at 11 cable points up to 0.45 m inside a test mesh.

To see a cable interact with geometry, do one of these instead:

- **Let it fall.** Set **Pin Controls** to *Ends Only*, place the middle controls above the object, and play from
  frame 1. Gravity drapes the cable onto the mesh — no animation needed.
- **Animate the character, not the cable.** Set the character up as a collider and animate *it* through the
  draped cable. This is the intended workflow, and it is stable even at speed (measured: zero penetration with a
  collider crossing 36 m in 60 frames).

Because this is a simulation, always **play forward from frame 1** rather than scrubbing — the solver carries
state between frames, so jumping around the timeline shows partially-solved results.

This uses Blender 5.2's **Cloth Dynamics (Experimental)** node asset, which Blender itself labels experimental —
its behavior may change in future Blender point releases. Bone-attachment, tiers/presets, and baking are not
implemented yet (in progress).

## Repo layout

- `__init__.py` Blender add-on entry point (`bl_info`, register/unregister).
- `operators.py` Operators for creating cables.
- `properties.py` Scene settings and UI properties.
- `panel.py` 3D Viewport sidebar panel.
- `utils.py` Shared utility functions.
- `dynamics.py` Geometry Nodes cloth-dynamics setup for the Dynamics feature.
