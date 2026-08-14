bl_info = {
    "name": "Procedural Cable Generator",
    "author": "Vickussya",
    "version": (1, 0, 0),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar > Cable",
    "description": "Generate editable cable curves driven by control empties.",
    "category": "Object",
}

import bpy
from bpy.props import PointerProperty

from .operators import (
    PCG_OT_add_selected_colliders,
    PCG_OT_create_cable_from_object_chain,
    PCG_OT_create_cable_from_selection,
    PCG_OT_create_cables_from_out_mid_in,
    PCG_OT_create_free_cable,
    PCG_OT_make_cable_dynamic,
    PCG_OT_remove_cable_dynamics,
)
from .panel import PCG_PT_cable_panel
from .properties import PCG_DynamicsSettings, PCG_Settings


_CLASSES = (
    PCG_Settings,
    PCG_DynamicsSettings,
    PCG_OT_create_cable_from_selection,
    PCG_OT_create_cable_from_object_chain,
    PCG_OT_create_free_cable,
    PCG_OT_create_cables_from_out_mid_in,
    PCG_OT_make_cable_dynamic,
    PCG_OT_remove_cable_dynamics,
    PCG_OT_add_selected_colliders,
    PCG_PT_cable_panel,
)


def register():
    # Classic add-on registration entry point used by Blender Preferences > Add-ons.
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.pcg_settings = PointerProperty(type=PCG_Settings)
    bpy.types.Object.pcg_dynamics = PointerProperty(type=PCG_DynamicsSettings)


def unregister():
    # Unregister in reverse order to avoid dependency issues.
    del bpy.types.Object.pcg_dynamics
    del bpy.types.Scene.pcg_settings
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
