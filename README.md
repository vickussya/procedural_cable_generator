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

## Repo layout

- `__init__.py` Blender add-on entry point (`bl_info`, register/unregister).
- `operators.py` Operators for creating cables.
- `properties.py` Scene settings and UI properties.
- `panel.py` 3D Viewport sidebar panel.
- `utils.py` Shared utility functions.
