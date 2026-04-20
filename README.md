# Procedural Cable Generator (Blender Add-on)

Simple add-on that creates a cable as a Bezier curve driven by control empties.

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

- `__init__.py` Blender add-on entry point (`bl_info`, register/unregister).
- `operators.py` Operators for creating cables.
- `properties.py` Scene settings and UI properties.
- `panel.py` 3D Viewport sidebar panel.
- `utils.py` Shared utility functions.
