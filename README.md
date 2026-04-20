# Procedural Cable Generator (Blender Add-on)

Simple add-on that creates a cable as a Bezier curve driven by control empties.

## Background

This tool started as a small workflow script during an environment scene project, to automate repetitive cable setup
and make layout/iteration faster while experimenting with cable routing and dressing.

## Install

This repo supports both install types:

### Blender Extensions (recommended for Blender 4.2+ / Blender 5+)

1. Download the repository as a zip (or zip the repo folder).
2. In Blender: `Edit > Preferences > Extensions > Install from Disk...`
3. Select the zip and enable **Procedural Cable Generator**.

This works because the repo root includes:
- `__init__.py` (entry point)
- `blender_manifest.toml` (extension manifest)

### Legacy add-on (older Blender versions)

1. Zip only the folder `procedural_cable_generator/` so the zip contains `procedural_cable_generator/__init__.py`.
2. In Blender: `Edit > Preferences > Add-ons > Install...`
3. Select that zip and enable **Procedural Cable Generator**.

## Use (v1)

1. Select exactly **two** objects in the viewport.
2. Make sure the **active** object is the start (last selected).
3. Open: `View3D > Sidebar (N) > Cable > Cable Generator`
4. Set:
   - **Cable Name**
   - **Middle Controls** (0 = straight-ish, higher = curvier)
   - **Slack** (negative values sag)
   - **Thickness** and **Bevel Resolution**
5. Click **Create Cable From Selection**

The add-on creates:
- A `CABLE_*` curve object
- Control empties `CTRL_*_START`, `CTRL_*_MID_XX`, `CTRL_*_END`
- A dedicated collection under `Procedural Cables`

Moving the control empties updates the cable shape.

## Legacy mode

If you already have empties named like `OUT_01`, `MID_01`, `IN_01`, you can enable **Show Legacy Tools**
in the panel and run **Create Cables From OUT/MID/IN**.

## Repo layout

- `__init__.py` Repo-zip entry point (keeps whole-repo ZIP installable).
- `blender_manifest.toml` Blender Extensions manifest (Blender 4.2+ / Blender 5+).
- `procedural_cable_generator/__init__.py` Blender add-on implementation entry point (register/unregister).
- `procedural_cable_generator/operators.py` Operators for creating cables.
- `procedural_cable_generator/props.py` Scene settings and UI properties.
- `procedural_cable_generator/ui.py` 3D Viewport sidebar panel.
- `procedural_cable_generator/utils.py` Shared utility functions.
