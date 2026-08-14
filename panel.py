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
                # Label on its own row: the property name is truncated to "Pin Cont..." when
                # drawn inline in a narrow sidebar.
                col = box.column(align=True)
                col.label(text="Pin Controls:")
                col.prop(dyn, "pin_mode", text="")

                col = box.column(align=True)
                col.label(text="Collision Collection:")
                col.prop(dyn, "collision_collection", text="")

                # The two ways collision silently does nothing: no colliders assigned, or
                # every control pinned so the cable is held rigid and cannot drape onto them.
                if dyn.collision_collection is None:
                    warn = box.column(align=True)
                    warn.label(text="No colliders assigned.", icon="ERROR")
                    warn.label(text="Use Collision Setup below.")
                elif dyn.pin_mode == "ALL":
                    warn = box.column(align=True)
                    warn.label(text="All controls pinned.", icon="ERROR")
                    warn.label(text="Pins override collision, so the")
                    warn.label(text="cable is dragged through mesh.")
                    warn.label(text="Use Ends Only to collide.")

                adv = box.box()
                adv.label(text="Advanced (raise with care):")
                adv.prop(dyn, "substeps")
                adv.prop(dyn, "constraint_steps")
                adv.prop(dyn, "segment_divisions")

                box.operator(PCG_OT_remove_cable_dynamics.bl_idname, icon="X")
            else:
                box.label(text="Uses Blender 5.2's experimental node-based cloth solver.")
                box.operator(PCG_OT_make_cable_dynamic.bl_idname, icon="PHYSICS")

        # Kept outside the cable-gated section above: setting up colliders means selecting
        # the character/prop meshes, at which point no cable is active and that section is
        # hidden - which would hide this button exactly when it is needed.
        layout.separator()
        collider_box = layout.box()
        collider_box.label(text="Collision Setup:", icon="MOD_PHYSICS")
        collider_box.operator(PCG_OT_add_selected_colliders.bl_idname, icon="MOD_PHYSICS")
        collider_box.label(text="Select character/prop meshes, then click.")
