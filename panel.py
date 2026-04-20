import bpy

from .operators import (
    PCG_OT_create_cable_from_object_chain,
    PCG_OT_create_cable_from_selection,
    PCG_OT_create_cables_from_out_mid_in,
    PCG_OT_create_free_cable,
)


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
