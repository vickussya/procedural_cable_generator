import bpy

from .operators import PCG_OT_create_cable_from_selection, PCG_OT_create_cables_from_out_mid_in
from .props import PCG_Settings


class PCG_PT_cable_panel(bpy.types.Panel):
    bl_label = "Cable Generator"
    bl_idname = "PCG_PT_cable_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cable"

    def draw(self, context: bpy.types.Context):
        settings: PCG_Settings = context.scene.pcg_settings
        layout = self.layout

        col = layout.column(align=True)
        col.label(text="Create From Selection:")
        col.prop(settings, "cable_name")
        col.prop(settings, "middle_controls")
        col.prop(settings, "slack")
        col.prop(settings, "thickness")
        col.prop(settings, "bevel_resolution")
        col.prop(settings, "empty_size")
        col.prop(settings, "parent_end_controls")
        col.operator(PCG_OT_create_cable_from_selection.bl_idname, icon="CURVE_BEZCURVE")

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
        layout.label(text="Tip: select exactly 2 objects.")
        layout.label(text="Active object is Start.")

