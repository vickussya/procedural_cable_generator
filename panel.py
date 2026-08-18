import bpy

from . import dynamics
from .operators import (
    PCG_OT_create_cable_from_object_chain,
    PCG_OT_create_cable_from_selection,
    PCG_OT_create_cables_from_out_mid_in,
    PCG_OT_create_free_cable,
    PCG_OT_create_coiled_cable,
    PCG_OT_create_cable_bundle,
    PCG_OT_add_selected_colliders,
    PCG_OT_attach_control,
    PCG_OT_bake_cable_to_mesh,
    PCG_OT_bake_simulation,
    PCG_OT_delete_simulation_bake,
    PCG_OT_detach_control,
    PCG_OT_disable_self_collision,
    PCG_OT_enable_self_collision,
    PCG_OT_export_cable_alembic,
    PCG_OT_copy_dynamics_settings,
    PCG_OT_make_cable_dynamic,
    PCG_OT_remove_cable_dynamics,
    selected_cables,
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

        box = layout.box()
        box.label(text="Coil / Roll:")
        col = box.column(align=True)
        col.label(text="Coil Preset:")
        col.prop(settings, "coil_preset", text="")
        box.prop(settings, "coil_seed")
        box.operator(PCG_OT_create_coiled_cable.bl_idname, icon="CURVE_NCIRCLE")

        shape = box.box()
        shape.label(text="Coil Shape:")
        shape.prop(settings, "coil_radius")
        shape.prop(settings, "coil_radius_end")
        shape.prop(settings, "coil_turns")
        shape.prop(settings, "coil_pitch")
        shape.prop(settings, "coil_controls_per_turn")
        shape.prop(settings, "coil_randomness")
        col = shape.column(align=True)
        col.label(text="Coil Axis:")
        col.prop(settings, "coil_axis", text="")

        box = layout.box()
        box.label(text="Tied Bundle (2 Objects):")
        box.prop(settings, "bundle_count")
        box.prop(settings, "bundle_spread")
        box.prop(settings, "bundle_variation")
        box.prop(settings, "bundle_seed")
        box.label(text="Uses Middle Controls + Slack above.")
        box.operator(PCG_OT_create_cable_bundle.bl_idname, icon="CURVE_BEZCURVE")

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
        cables = selected_cables(context)
        if cable is not None:
            layout.separator()
            box = layout.box()
            header = box.row()
            header.label(text="Dynamics (Experimental):", icon="PHYSICS")
            if cable is not active:
                # Active object is one of this cable's controls, so name the cable it drives.
                box.label(text=f"Cable: {cable.name}", icon="OUTLINER_OB_CURVE")

            # The buttons below act on every selected cable, so say how many that is - a
            # Tied Bundle leaves several selected and all of them are affected. The settings
            # themselves are stored per cable, hence the toggle: on, editing any of them
            # below edits all of the selected cables at once.
            if len(cables) > 1:
                box.label(text=f"{len(cables)} cables selected.", icon="OUTLINER_OB_CURVE")
                box.prop(settings, "sync_selected_cables", toggle=True, icon="LINKED")
                # Still offered with the toggle on, to re-align cables that were tuned
                # separately before it was switched on.
                if dynamics.is_dynamics_enabled(cable):
                    box.operator(PCG_OT_copy_dynamics_settings.bl_idname, icon="DUPLICATE")

            if dynamics.is_dynamics_enabled(cable):
                dyn = cable.pcg_dynamics
                col = box.column(align=True)
                col.label(text="Tier:")
                col.prop(dyn, "tier", text="")

                if dyn.tier == "BACKGROUND":
                    col = box.column(align=True)
                    col.label(text="Sway (no collision):")
                    col.prop(dyn, "sway_amount")
                    col.prop(dyn, "sway_speed")
                    col.prop(dyn, "sway_scale")
                    col.prop(dyn, "sway_resample")
                else:
                    col = box.column(align=True)
                    col.label(text="Preset:")
                    col.prop(dyn, "preset", text="")

                    col = box.column(align=True)
                    col.label(text="Appearance:")
                    col.prop(dyn, "thickness")
                    col.prop(dyn, "profile_resolution")

                    col = box.column(align=True)
                    col.label(text="Physics:")
                    col.prop(dyn, "mass")
                    col.prop(dyn, "stiffness")
                    col.prop(dyn, "bend")
                    col.prop(dyn, "damping")
                    col.prop(dyn, "friction")
                    col.prop(dyn, "collision_radius")

                    box.separator()
                    # Label on its own row: the property name is truncated to "Pin Cont..."
                    # when drawn inline in a narrow sidebar.
                    col = box.column(align=True)
                    col.label(text="Pin Controls:")
                    col.prop(dyn, "pin_mode", text="")

                    col = box.column(align=True)
                    col.label(text="Collision Collection:")
                    col.prop(dyn, "collision_collection", text="")

                    # The two ways collision silently does nothing: no colliders assigned,
                    # or every control pinned so the cable is held rigid and cannot drape.
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

                    selfcol = box.box()
                    selfcol.label(text="Self Collision (heavy):", icon="MOD_PHYSICS")
                    if dyn.use_self_collision:
                        selfcol.label(text="On - legacy cloth solver.")
                        selfcol.prop(dyn, "self_collision_distance")
                        selfcol.operator(PCG_OT_disable_self_collision.bl_idname, icon="X")
                    else:
                        selfcol.label(text="Off. Lets a cable tangle with")
                        selfcol.label(text="itself, but costs performance.")
                        selfcol.operator(PCG_OT_enable_self_collision.bl_idname, icon="MOD_PHYSICS")

                    bake = box.box()
                    bake.label(text="Bake:", icon="FILE_TICK")
                    row = bake.row(align=True)
                    row.operator(PCG_OT_bake_simulation.bl_idname, icon="PHYSICS")
                    row.operator(PCG_OT_delete_simulation_bake.bl_idname, text="", icon="TRASH")
                    bake.operator(PCG_OT_bake_cable_to_mesh.bl_idname, icon="OUTLINER_OB_MESH")
                    col = bake.column(align=True)
                    col.label(text="Alembic Export Folder:")
                    col.prop(dyn, "alembic_directory", text="")
                    col.operator(PCG_OT_export_cable_alembic.bl_idname, icon="EXPORT")
                    if not bpy.data.is_saved:
                        warn = bake.column(align=True)
                        warn.label(text="Unsaved .blend: exports go to", icon="ERROR")
                        warn.label(text="a temp folder. Save first.")

                # A partially set-up selection (some cables added later, say) can be
                # completed without deselecting the ones already dynamic.
                if any(not dynamics.is_dynamics_enabled(c) for c in cables):
                    box.operator(
                        PCG_OT_make_cable_dynamic.bl_idname,
                        text="Make Remaining Dynamic",
                        icon="PHYSICS",
                    )

                box.operator(PCG_OT_remove_cable_dynamics.bl_idname, icon="X")
            else:
                box.label(text="Uses Blender 5.2's experimental node-based cloth solver.")
                box.operator(PCG_OT_make_cable_dynamic.bl_idname, icon="PHYSICS")

        # The sections below stay outside the cable-gated block above, because both
        # workflows end with a non-cable object active (an armature, or the collider
        # meshes), which would otherwise hide the very buttons needed.
        layout.separator()
        attach_box = layout.box()
        attach_box.label(text="Attach Controls:", icon="CONSTRAINT_BONE")
        attach_box.operator(PCG_OT_attach_control.bl_idname, icon="CONSTRAINT_BONE")
        attach_box.operator(PCG_OT_detach_control.bl_idname, icon="X")
        attach_box.label(text="Select CTRL empties, then the")
        attach_box.label(text="bone or object last.")

        layout.separator()
        collider_box = layout.box()
        collider_box.label(text="Collision Setup:", icon="MOD_PHYSICS")
        collider_box.operator(PCG_OT_add_selected_colliders.bl_idname, icon="MOD_PHYSICS")
        collider_box.label(text="Select character/prop meshes, then click.")
        collider_box.label(text="Select cables too to assign them.")
