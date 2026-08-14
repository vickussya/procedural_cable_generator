import bpy

from . import dynamics
from .operators import (
    PCG_OT_create_cable_from_object_chain,
    PCG_OT_create_cable_from_selection,
    PCG_OT_create_cables_from_out_mid_in,
    PCG_OT_create_free_cable,
    PCG_OT_add_selected_colliders,
    PCG_OT_make_cable_dynamic,
    PCG_OT_remove_cable_dynamics,
)
from .utils import is_cable_curve_object


class PCG_PT_cable_panel(bpy.types.Panel):
    bl_label = "Cable Generator"
    bl_idname = "PCG_PT_cable_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cable"

    def draw(self, context: bpy.types.Context):
        settings = context.scene.pcg_settings
        layout = self.layout

        col = layout.column(align=True)
        col.label(text="Cable Settings:")
        col.prop(settings, "cable_name")
        col.prop(settings, "slack")
        col.prop(settings, "thickness")
        col.prop(settings, "bevel_resolution")
        col.prop(settings, "empty_size")

        layout.separator()

        box = layout.box()
        box.label(text="From 2 Objects:")
        box.prop(settings, "middle_controls")
        box.prop(settings, "parent_end_controls")
        box.operator(PCG_OT_create_cable_from_selection.bl_idname, icon="CURVE_BEZCURVE")

        box = layout.box()
        box.label(text="From Selected Objects (Chain):")
        box.prop(settings, "chain_order")
        box.prop(settings, "parent_chain_controls")
        box.operator(PCG_OT_create_cable_from_object_chain.bl_idname, icon="CURVE_BEZCURVE")

        box = layout.box()
        box.label(text="Free Cable:")
        box.prop(settings, "free_controls")
        box.prop(settings, "free_length")
        box.operator(PCG_OT_create_free_cable.bl_idname, icon="CURVE_BEZCURVE")

        layout.separator()
        layout.prop(settings, "show_legacy", toggle=True)
        if settings.show_legacy:
            box = layout.box()
            box.label(text="Legacy OUT/MID/IN:")
            box.prop(settings, "legacy_out_prefix")
            box.prop(settings, "legacy_mid_prefix")
            box.prop(settings, "legacy_in_prefix")
            box.operator(PCG_OT_create_cables_from_out_mid_in.bl_idname, icon="OUTLINER_OB_EMPTY")

        layout.separator()
        layout.label(text="Tip: move CTRL empties to shape cables.")

        active = context.active_object
        cable = dynamics.resolve_cable_for_object(active)
        if cable is not None:
            layout.separator()
            box = layout.box()
            header = box.row()
            header.label(text="Dynamics (Experimental):", icon="PHYSICS")
            if cable is not active:
                # Active object is one of this cable's controls, so name the cable it drives.
                box.label(text=f"Cable: {cable.name}", icon="OUTLINER_OB_CURVE")

            if dynamics.is_dynamics_enabled(cable):
                dyn = cable.pcg_dynamics
                col = box.column(align=True)
                col.prop(dyn, "mass")
                col.prop(dyn, "stiffness")
                col.prop(dyn, "bend")
                col.prop(dyn, "damping")
                col.prop(dyn, "friction")
                col.prop(dyn, "collision_radius")

                box.separator()
                box.prop(dyn, "pin_mode")
                if dyn.pin_mode == "ALL":
                    box.label(text="Ends Only frees the cable to drape.", icon="INFO")

                col = box.column(align=True)
                col.label(text="Collision:")
                col.prop(dyn, "collision_collection", text="")
                col.operator(PCG_OT_add_selected_colliders.bl_idname, icon="MOD_PHYSICS")

                adv = box.box()
                adv.label(text="Advanced (raise with care):")
                adv.prop(dyn, "substeps")
                adv.prop(dyn, "constraint_steps")
                adv.prop(dyn, "segment_divisions")

                box.operator(PCG_OT_remove_cable_dynamics.bl_idname, icon="X")
            else:
                box.label(text="Uses Blender 5.2's experimental node-based cloth solver.")
                box.operator(PCG_OT_make_cable_dynamic.bl_idname, icon="PHYSICS")
