# Procedural Cable Generator 1.1.0

Editable cables in one click: Bezier curves you shape by dragging control empties. This release adds **coils** and
**tied bundles**, one-click **look presets**, and **Dynamics (Experimental)**: cables that sag, drape over
characters and props, follow bones and bake out. Everything except Dynamics runs on **Blender 4.2 LTS and newer**.

Built for, and used in, my short animated film *Oops*, for the cables in its lab scene.

## Highlights

- **Coil / Roll**: drop a coil of cable at the 3D cursor with one click. Presets: *Ground Coil*, *Hank*,
  *Cable Drum*, *Loose Heap*. Seed gives a different variation of the same look.
- **Tied Bundle**: several cables between two objects, tied together at both ends and fanning out between them.
- **Cable presets**: *Power Line*, *Street Wires*, *Sagging Drop*, *Cable Loom*, *Taut Run*. Each sets the sag,
  control count, thickness and bundle settings together.
- **Span Sag**: sag as a fraction of the distance, so a look holds up on a 4 m run and a 30 m one alike.
- **Dynamics (Experimental, Blender 5.2+)**:
  - **Make Dynamic** on any cable, no need to recreate it. It is pinned at its controls and sags between them.
  - **Hero** (full simulation) or **Background** (cheap procedural sway) per cable.
  - **Pin Controls**: all controls, ends only, or none.
  - **Collision** with characters and props through *Add Selected As Colliders*, including animated and rigged
    meshes.
  - **Attach Controls** to a bone or object, so a cable end follows a hand or a prop.
  - **Bake** to Blender's simulation cache, a self-contained baked mesh, or Alembic (`.abc`).
  - Optional **Self Collision** so coils and heaps don't pass through themselves.
  - Every Dynamics button and setting can act on all selected cables at once, so a whole bundle is set up in
    one click.

The full list of changes is in [CHANGELOG.md](https://github.com/vickussya/procedural_cable_generator/blob/main/CHANGELOG.md).

## Supported Blender versions

| | Blender 4.2 LTS – 5.1 | Blender 5.2 LTS and newer |
|---|---|---|
| Creating and shaping cables (all modes, presets, attach controls) | ✅ | ✅ |
| Dynamics (simulation, collision, baking) | Not available: the panel says "Needs Blender 5.2 or newer." | ✅ Experimental |

Tested on Blender 4.2.23 LTS, 4.5.2 LTS and 5.2.0 LTS, on Windows.

## Install

1. Download **`procedural_cable_generator-1.1.0.zip`** from the *Assets* below. Don't unzip it.
2. In Blender: **Edit › Preferences › Add-ons**, open the **⌄** menu at the top right and choose
   **Install from Disk…**.
3. Select the ZIP. Make sure **Procedural Cable Generator** is enabled.
4. In the 3D Viewport press **N** and open the **Cable** tab.

> **Use the ZIP from these Assets, not the green "Code › Download ZIP" button.** That button packs the repository
> into a folder named after the branch (e.g. `procedural_cable_generator-release-1.1.0`), and Blender can't load an
> add-on whose folder name isn't a valid Python module name, so it fails with "No module named …"; the ZIP above
> is built to install as-is.

**Upgrading from 1.0.0?** Restart Blender after installing. Blender keeps the old version loaded until then,
and the add-on can fail to enable with a "cannot import name" error.

New to the add-on? The [README](https://github.com/vickussya/procedural_cable_generator/blob/main/README.md) has a five-step quick start.

## Known limitations

- **Dynamics is Experimental.** It is built on Blender 5.2's own *Cloth Dynamics (Experimental)* node, so its
  behaviour may change in future Blender releases. It needs Blender 5.2 or newer.
- **Self Collision is heavy.** It is noticeably slower than the normal solver, because it routes the cable
  through Blender's older Cloth simulation on a hidden ribbon. Slack cables can buckle sideways more than a round
  cable would, and pinned controls are held by a spring rather than exactly. Hero tier only. Turn it on only where
  tangling is actually visible.
- **Play simulations forward from frame 1.** Scrubbing the timeline shows half-solved results. Make sure animated
  colliders are in their frame-1 position before pressing Play.
- **Pinned controls win over collision.** Animating a pinned control into a mesh drags the cable through it.
  To collide, use *Pin Controls: Ends Only*, or animate the collider rather than the cable.
- **Background-tier cables don't collide.** They only sway.
- **Cable Settings apply to new cables.** To change an existing cable, move its controls or edit its curve
  (see *Changing a cable after it exists* in the README).

## Checksum

SHA-256 of `procedural_cable_generator-1.1.0.zip`:

```
e47d8e5e764956db34ac027e1409bba39436c45d1c736029bcba1a80c566a7cb
```
