"""
Repository-root add-on entry point.

Why this exists:
- Installing a ZIP of the whole repository in Blender creates an add-on folder that (previously) did not contain an
  `__init__.py` at the top level, so Blender couldn't detect/register the add-on.
- Blender's Extensions system (Blender 4.2+ / Blender 5+) expects a top-level entry point plus a manifest.

This file keeps the add-on discoverable for both:
- Classic "legacy add-on" installs (uses `bl_info`).
- Blender Extensions installs (uses `blender_manifest.toml`).
"""

bl_info = {
    "name": "Procedural Cable Generator",
    "author": "procedural_cable_generator contributors",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Cable",
    "description": "Generate editable cable curves driven by control empties.",
    "category": "Object",
}


def register():
    from .procedural_cable_generator import register as _register

    _register()


def unregister():
    from .procedural_cable_generator import unregister as _unregister

    _unregister()

