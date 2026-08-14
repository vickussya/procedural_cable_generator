# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> Note: this project has no prior git tags/releases. The `[1.0.0]` entry below is a retroactive **baseline /
> pre-dynamics snapshot** of the add-on's state on `main` as of 2026-08-14, versioned to match `bl_info["version"]`,
> not an actual tagged release date.

## [Unreleased]

### Added
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
