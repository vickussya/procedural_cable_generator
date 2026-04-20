# AGENTS.md

Instructions for Codex/AI agents working in this repository.

## Project

This repo contains a Blender add-on packaged as `procedural_cable_generator/`.

## Scope and priorities

- Keep changes focused on the add-on (v1: simple, stable, artist-friendly).
- Prefer Blender-native, non-deprecated API patterns compatible with current Blender releases.
- Avoid unnecessary complexity (no extra dependencies, no over-engineering).

## Add-on structure

- Add-on entry point: `procedural_cable_generator/__init__.py`
- Modules:
  - `procedural_cable_generator/operators.py`
  - `procedural_cable_generator/props.py`
  - `procedural_cable_generator/ui.py`
  - `procedural_cable_generator/utils.py`

When adding new functionality, keep related code in the appropriate module rather than growing `__init__.py`.

## Coding conventions

- Use clear, descriptive names; avoid single-letter variables except for short loops.
- Prefer small helper functions in `utils.py` over duplicated logic.
- Keep UI labels/props concise and artist-friendly.
- Don’t add heavy inline comments; add short comments only where Blender behavior is non-obvious.

## Behavior conventions

- Generated objects should be organized under the `Procedural Cables` collection.
- Use consistent naming (`CABLE_*`, `CTRL_*`) and avoid clutter.
- Preserve legacy support for `OUT_*`, optional `MID_*`, `IN_*` where practical.

## Testing

- This add-on is best validated inside Blender:
  - Install by zipping the `procedural_cable_generator/` folder (zip must contain `procedural_cable_generator/__init__.py`).
  - Enable the add-on and test creation from a two-object selection.
  - Verify moving control empties updates the curve.

## Git workflow

- Don’t rewrite history unless explicitly asked.
- Keep commits small and descriptive when requested to commit.

