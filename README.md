# Procedural Cable Generator (Blender Add-on)

Creates cables as Bezier curves driven by control empties, and can optionally simulate them so they sag, drape over
characters and props, get dragged along, and tangle.

## Background

This tool started as a small workflow script during an environment scene project, to automate repetitive cable setup
and make layout/iteration faster while experimenting with cable routing and dressing.

## Install

A **classic Blender add-on**, targeting **Blender 5.2 LTS**. The add-on root is the repository folder itself (it
contains `__init__.py`).

1. Code > download zip.
2. In Blender: `Edit > Preferences > Add-ons > Install...`
3. Select that zip and enable **Procedural Cable Generator**.

The panel appears at `View3D > Sidebar (N) > Cable > Cable Generator`.

> **Upgrading?** Restart Blender after reinstalling. Blender keeps the previous version's modules loaded, and the
> add-on will fail to enable with a "cannot import name" error until it is restarted.

---

## How it works

Worth reading once — it explains why the settings behave the way they do.

### A cable is a curve plus control empties

Every creation mode produces the same two things inside a collection under `Procedural Cables`:

- a **`CABLE_*` Bezier curve** — the visible cable, given its thickness by Blender's curve bevel;
- a set of **`CTRL_*` empties** — one per curve point.

Each curve point is wired to its empty by a **driver** that reads the empty's world position. So moving an empty
moves the cable, and that keeps working no matter how the empty got there — dragged by hand, parented to a prop, or
following an armature bone. This is the whole static system, and it never runs any Python while you work.

### Dynamics replaces the cable's geometry, it doesn't move the curve points

When you click **Make Dynamic**, a Geometry Nodes modifier is added to the curve. It ignores the curve's own points
and rebuilds the cable from scratch each frame:

1. A hidden helper mesh, **`PINS_<cable>`**, holds one vertex per `CTRL_*` empty, each following its empty with a
   Hook modifier. This is the bridge between your controls and the simulation.
2. Those vertices are joined into a path, smoothed, and **subdivided** into the simulated points
   (*Divisions Per Segment* controls how many).
3. Because subdivision is even, the original controls land on **known indices**, so they can be pinned at full
   strength — which is why posed controls hold *exactly* rather than approximately.
4. Blender 5.2's **Cloth Dynamics** node solves the result, using your Mass / Stiffness / Bend / Damping settings.
5. The solved points are converted back to a curve and **beveled into a tube** inside the same node tree.

Two consequences worth knowing:

- **The `CTRL_*` empties are inputs, not outputs.** They keep showing where you posed them; the simulated cable is
  the modifier's output. This is also why "bake to keyframes" on the curve isn't offered — the simulated shape
  isn't in the curve points to keyframe.
- **No Python runs per frame.** Everything is evaluated by Blender's own dependency graph, so playback speed is
  Blender's, not the add-on's.

### Helper objects you'll see in the outliner

| Name | What it is | Safe to delete? |
|---|---|---|
| `CABLE_*` | The visible cable curve | It *is* the cable |
| `CTRL_*` | Control empties — move these to shape the cable | No, the cable follows them |
| `PINS_*` | Hidden bridge between controls and the solver | No — removed automatically by *Remove Dynamics* |
| `CLOTH_*` | Hidden ribbon simulated by legacy cloth, only when Self Collision is on | No — removed by *Disable Self Collision* |
| `BAKED_*` | Result of *Convert To Baked Mesh* | Yes, it's an output |
| `Cable Colliders` | Collection of objects cables can hit | It's just a collection |

---

## Creating cables

All modes share **Cable Settings** at the top of the panel: *Cable Name*, *Slack* (negative sags), *Thickness*,
*Bevel Resolution* and *Control Size*.

### 1) From 2 Objects

1. Select exactly **two** objects; the **active** one (last selected) is the start.
2. Set **Middle Controls** (0 = straighter, more = curvier).
3. Optionally enable **Parent End Controls** so the ends follow those objects.
4. Click **Create Cable From 2 Selected Objects**.

### 2) From Selected Objects (Chain)

Routes one cable through **2+ objects** — useful for running a cable across props.

1. Select two or more objects.
2. Set **Chain Order** — *Nearest* (nearest-neighbour from the active object), *Selection* (Blender's order), or
   *Name*.
3. Optionally enable **Parent Chain Controls**.
4. Click **Create Cable From Selected Objects (Chain)**.

### 3) Free Cable (Cursor)

Controls only, no selection needed. Place the 3D cursor, set **Free Controls** and **Free Length**, and click
**Create Free Cable (Cursor)**. Then route it by moving the empties.

### 4) Coil / Roll (Cursor)

For a coil of cable dropped on the ground, a hank on a hook, or a drum on a reel.

1. Place the 3D cursor where the coil should sit.
2. Pick a **Coil Preset** and click **Create Coiled Cable (Cursor)**. That's the whole workflow:

   | Preset | Look |
   |---|---|
   | **Ground Coil** | Nested rings spiralling outward, sitting flat — cable coiled and dropped |
   | **Hank** | Tight, slightly messy loop, as carried or hung on a hook |
   | **Cable Drum** | Neatly wound on a reel, standing on its side |
   | **Loose Heap** | Wide, irregular, untidy pile |

3. **Seed** gives a different random variation of the same preset.

Under **Coil Shape** you can override the details, which switches the preset to *Custom*:

- **Inner / Outer Radius** — a larger outer radius spirals outward, which is how cable actually coils. Equal values
  give a uniform drum.
- **Pitch** — rise per turn. Keep it tiny (a centimetre or two) for a coil lying flat; large values give a spring.
- **Controls Per Turn** — roundness. **Randomness** — how hand-wound it looks. **Coil Axis** — `Z` winds upward as
  if dropped, `Y`/`X` wind on their side like a reel.

The coil's shape is *generated*, not simulated into place, because relying on physics to coil a cable is
unreliable. It's a normal cable afterwards, so it can be reshaped and made dynamic.

### 5) Tied Bundle (2 Objects)

Several cables running together and cinched at both ends — a loom or zip-tied run.

1. Select exactly **two** objects (active is the start).
2. Set **Cables**, **Spread** (how far they separate mid-run) and **Variation** (how much they differ). **Seed**
   reshuffles. It also uses **Middle Controls** and **Slack** from the top of the panel.
3. Click **Create Tied Bundle From 2 Objects**.

The cables meet exactly at the two objects and fan out between them — that convergence is what reads as "tied".
Each cable gets its own collection and controls, so you can shape or simulate them individually, including making
one Hero and the rest Background.

### Legacy mode

If you already have empties named `OUT_01`, `MID_01`, `IN_01`, enable **Show Legacy Tools** and run
**Create Cables From OUT/MID/IN**.

### Changing a cable after it exists

**Cable Settings** apply to *newly created* cables only — they don't retro-edit existing ones.

| What you want | Static cable | Dynamic cable |
|---|---|---|
| Thickness | `Object Data > Geometry > Bevel > Depth` | **Appearance > Thickness** |
| Cross-section roundness | `Object Data > Geometry > Bevel > Resolution` | **Appearance > Profile Resolution** |
| Smoothness along its length | `Object Data > Shape > Resolution Preview U` | **Advanced > Divisions Per Segment** |
| Shape | Move the `CTRL_*` empties | Move the `CTRL_*` empties |

On a dynamic cable the Appearance settings also write back to the curve, so it keeps its look if you later remove
dynamics.

---

## Dynamics (Experimental)

Requires **Blender 5.2 LTS**. Any cable can be simulated without recreating it. This is built on Blender's
**Cloth Dynamics (Experimental)** node asset — Blender itself labels it experimental, so behaviour may shift in
future point releases.

### Quick start

1. Select a `CABLE_*` curve.
2. Click **Make Dynamic**.
3. Go to **frame 1** and press **Play**. The cable is pinned at its controls and sags between them.
4. Tweak settings live while it plays.
5. **Remove Dynamics** returns it to plain driver-based control at any time.

> **Play forward from frame 1, don't scrub.** The solver carries state between frames, so jumping around the
> timeline shows half-solved results that look broken.

### Working on several cables at once

A **Tied Bundle** is several separate cables, and so is a set of coils. Every dynamics button acts on **all
selected cables**, not just the active one — select them (they are already selected right after generating) and
click once. Selecting a `CTRL_*` empty counts as selecting the cable it drives. The panel shows how many cables
your click will affect.

Dynamics settings are stored **per cable**, so a slider only changes the active one. Tune that cable, then click
**Copy Settings To Selected** to push its settings onto the rest of the selection.

### Tier: Hero or Background

Per cable, so a shot can mix a few expensive cables with many cheap ones.

- **Hero** — full cloth simulation with pinning and collision. For cables the shot features.
- **Background** — cheap procedural sway: no solver, no collision, ends held still. For the many cables that only
  need to look alive. Measured at roughly an eighth of Hero's cost.

Background cables get their own *Sway Amount / Speed / Scale / Resolution* and ignore the physics and collision
settings entirely. Switching tier is instant and reversible.

### Pin Controls

Which `CTRL_*` empties hold the cable while it simulates. This is the setting that most often explains "why isn't
it doing what I expect".

- **All Controls** (default) — every control pinned, so the cable keeps the pose you set. Use for **coils** and any
  shape you posed deliberately.
- **Ends Only** — only the first and last pinned. Middle controls still shape the rest path, but the span between
  them is free to sag, drape and collide. **Required for a cable to interact with anything.**
- **None** — nothing pinned; the whole cable falls.

A pinned control is a **hard constraint** the solver cannot overrule. That's what makes posed controls exact, and
it's also why an all-pinned cable can't drape onto a collider.

### Presets

*Floppy Wire*, *Heavy Cable* and *Frayed Tangle* set thickness, mass, stiffness, bend, damping, friction and
resolution together. Editing any of them switches to *Custom*.

**Mass and Bend don't change the shape of a cable once it has settled.** A hanging cable's shape is set by its
length and span, much as a pendulum's period is independent of its mass. They change how it responds to being
pushed or dragged, which is where the presets visibly differ. If you raise Mass expecting more droop, add slack
instead.

### Physics settings

- **Mass** — weight and momentum when something moves the cable.
- **Stiffness** — resistance to stretching along its length.
- **Bend Resistance** — resistance to kinking. Low is floppy wire, high is stiff hose.
- **Damping** — how quickly motion settles. Raise it if a cable keeps swinging.
- **Friction** — how much it grips surfaces it slides across.
- **Collision Radius** — effective thickness for contact, independent of the visual *Thickness*.

**Advanced** (costs performance): **Substeps** / **Constraint Steps** for solver accuracy, and
**Divisions Per Segment** for how many simulated points sit between each pair of controls.

### Collision with characters and props

1. Select the character/prop **meshes** the cable should hit — and, if you want them assigned right away, the
   dynamic cables too.
2. Click **Add Selected As Colliders** under *Collision Setup* at the bottom of the panel. They get a collider
   modifier and land in a `Cable Colliders` collection, which is assigned to every selected dynamic cable. With no
   cable in the selection it falls back to any dynamic cable that has no collision collection yet.
3. Set the cables' **Pin Controls** to *Ends Only* so they have a free span.
4. Go to frame 1 and play.

A cable's own helper objects (`PINS_*`, `CLOTH_*`) are never turned into colliders, even though they are meshes
sitting in the cable's collection and get picked up by a box select.

The panel warns you in the two states where collision silently does nothing: no colliders assigned, or every
control pinned.

Colliders must be meshes and are set up as *deforming*, so animated and armature-driven characters work. Re-running
the operator updates existing colliders, so `F9` lets you retune **Margin** and **Friction** — raise Margin if
cables sink into thin or fast-moving geometry.

### Attaching controls to a character

1. Select the bone in **Pose Mode**, then return to Object Mode. Clicking a bone in the **Outliner is not enough** —
   Blender doesn't mark it selected, and the add-on will refuse rather than attach to the wrong thing.
2. Select the `CTRL_*` empties.
3. Shift-select the armature (or plain object) **last**, so it's active.
4. Click **Attach Controls To Active**. The status bar confirms which bone was used — if it names the armature
   instead of a bone, the bone wasn't selected in Pose Mode.

The control keeps its position and then follows the bone. Because pinned controls hold exactly, attaching one to a
hand bone makes the cable end track that hand while the rest simulates. **Detach Controls** releases them without
moving them.

### Baking

Three outputs, in the *Bake* box on a Hero cable. All use the scene's Frame Start/End range.

- **Bake Simulation** — fills Blender's native simulation cache so scrubbing is fast and stable. **Delete Bake**
  (trash icon) clears it. The cable still depends on the live setup.
- **Convert To Baked Mesh** — creates a `BAKED_<cable>` mesh with one animated shape key per frame. Fully
  self-contained: it keeps working even if you delete the cable, controls and colliders. Best for locking a shot
  down; the `.blend` grows with frame count.
- **Export Alembic (.abc)** — writes the evaluated cable out for rendering or handoff. **Export Folder** defaults
  to `//` (the folder holding the `.blend`) and can be overridden with the folder picker. If the `.blend` is
  unsaved, `//` has nowhere to point, so the export goes to a temp folder and warns you to save first.

### Self Collision (optional, heavy)

Lets a cable collide with **itself**, so coils, loops and heaps have volume instead of interpenetrating. Blender
5.2's node solver can't do this, so the cable is routed through Blender's older Cloth simulation on a hidden
`CLOTH_*` ribbon proxy, and drawn from that ribbon's centre line. **Off by default**, Hero tier only.

Turn it on with **Enable Self Collision** and tune **Self Distance** — how close the cable may come to itself
before pushing apart.

Use it only where tangling is visible: a cable spanning two points can never touch itself, so it would cost
performance for nothing.

Things to know:

- It is **noticeably slower** than the normal solver.
- **On a coil, use *All Controls*.** A coil is a posed shape; with *Ends Only* nothing holds its turns up, so it
  collapses and thrashes. That looks like a self-collision failure but is just an unsupported cable — measured 0.23
  of movement with *All Controls* against 6.4 with *Ends Only*.
- The proxy is a flat ribbon, so a slack cable can buckle sideways more than a round cable would, and pinned
  controls are held by a spring rather than exactly. If precise pinning matters more than tangling, leave it off.

---

## Gotchas

Behaviours that look like bugs but aren't:

- **Don't animate a pinned control into geometry.** A pin is a hard constraint, so the cable is dragged straight
  through the collider. Either let the cable fall onto the object (*Ends Only* + gravity), or animate the
  **character** through a draped cable — the intended workflow, stable even at speed.
- **Scrubbing shows half-solved results.** Play forward from frame 1.
- **Mass and Bend don't change a settled cable's shape.** See *Presets* above.
- **Cable Settings don't retro-edit existing cables.** See the table above.
- **A restart is needed after reinstalling the add-on.**

---

## Repo layout

- `__init__.py` — add-on entry point (`bl_info`, register/unregister).
- `operators.py` — all operators: the creation modes, dynamics, attachment, colliders and baking.
- `properties.py` — scene creation settings and per-cable dynamics settings.
- `panel.py` — the 3D Viewport sidebar panel.
- `utils.py` — shared helpers: collections, naming, empties, parenting, drivers, curve building, and the helix and
  bundle maths (plain functions, testable without Blender).
- `dynamics.py` — the Dynamics feature: Geometry Nodes trees, pin anchors, cloth proxies, colliders, bake helpers.

See [AGENTS.md](AGENTS.md) for conventions to follow when changing the code, and [CHANGELOG.md](CHANGELOG.md) for
what changed and why.

## License

GPL-3.0. See [LICENSE](LICENSE).
