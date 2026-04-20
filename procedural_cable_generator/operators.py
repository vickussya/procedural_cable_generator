import math

import bpy

from .props import PCG_Settings
from .utils import (
    create_cable_curve,
    ensure_root_collection,
    make_empty,
    new_child_collection,
    offset_dir_for_slack,
    ordered_selected_pair,
    parent_keep_world,
    unique_name,
)


class PCG_OT_create_cable_from_selection(bpy.types.Operator):
    bl_idname = "pcg.create_cable_from_selection"
    bl_label = "Create Cable From Selection"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        a, b = ordered_selected_pair(context)
        return a is not None and b is not None and context.mode == "OBJECT"

    def execute(self, context: bpy.types.Context):
        settings: PCG_Settings = context.scene.pcg_settings
        start_obj, end_obj = ordered_selected_pair(context)
        if not start_obj or not end_obj:
            self.report({"ERROR"}, "Select exactly two objects (active object is Start)")
            return {"CANCELLED"}

        root = ensure_root_collection(context.scene)
        cable_coll = new_child_collection(root, f"Cable_{settings.cable_name}")

        start_pos = start_obj.matrix_world.translation.copy()
        end_pos = end_obj.matrix_world.translation.copy()

        existing_obj_names = {o.name for o in bpy.data.objects}
        start_empty = make_empty(
            unique_name(f"CTRL_{settings.cable_name}_START", existing_obj_names),
            start_pos,
            settings.empty_size,
        )
        end_empty = make_empty(
            unique_name(f"CTRL_{settings.cable_name}_END", existing_obj_names | {start_empty.name}),
            end_pos,
            settings.empty_size,
        )

        if settings.parent_end_controls:
            parent_keep_world(start_empty, start_obj)
            parent_keep_world(end_empty, end_obj)

        cable_coll.objects.link(start_empty)
        cable_coll.objects.link(end_empty)

        offset_dir = offset_dir_for_slack(start_pos, end_pos)
        controls: list[bpy.types.Object] = [start_empty]

        for i in range(settings.middle_controls):
            t = (i + 1) / (settings.middle_controls + 1)
            base = start_pos.lerp(end_pos, t)
            offset = offset_dir * (settings.slack * math.sin(math.pi * t))
            mid_pos = base + offset
            mid_name = unique_name(
                f"CTRL_{settings.cable_name}_MID_{i + 1:02d}",
                {o.name for o in bpy.data.objects} | {c.name for c in controls} | {end_empty.name},
            )
            mid_empty = make_empty(mid_name, mid_pos, settings.empty_size)
            cable_coll.objects.link(mid_empty)
            controls.append(mid_empty)

        controls.append(end_empty)

        existing_names = {o.name for o in bpy.data.objects} | {c.name for c in bpy.data.curves}
        curve_name = unique_name(f"CABLE_{settings.cable_name}", existing_names)
        curve_obj = create_cable_curve(
            collection=cable_coll,
            cable_name=curve_name,
            controls=controls,
            thickness=settings.thickness,
            bevel_resolution=settings.bevel_resolution,
        )

        context.view_layer.objects.active = curve_obj
        curve_obj.select_set(True)
        self.report({"INFO"}, f"Created cable '{curve_obj.name}' with {len(controls)} controls")
        return {"FINISHED"}


class PCG_OT_create_cables_from_out_mid_in(bpy.types.Operator):
    bl_idname = "pcg.create_cables_from_out_mid_in"
    bl_label = "Create Cables From OUT/MID/IN"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context):
        settings: PCG_Settings = context.scene.pcg_settings
        out_prefix = settings.legacy_out_prefix
        mid_prefix = settings.legacy_mid_prefix
        in_prefix = settings.legacy_in_prefix

        outs = [o for o in bpy.data.objects if o.name.startswith(out_prefix)]
        if not outs:
            self.report({"WARNING"}, f"No objects found with prefix '{out_prefix}'")
            return {"CANCELLED"}

        root = ensure_root_collection(context.scene)
        legacy_coll = new_child_collection(root, "Legacy_OUT_MID_IN")

        created = 0
        for out_obj in outs:
            suffix = out_obj.name[len(out_prefix) :]
            in_obj = bpy.data.objects.get(f"{in_prefix}{suffix}")
            if not in_obj:
                continue
            mid_obj = bpy.data.objects.get(f"{mid_prefix}{suffix}")

            controls = [out_obj] + ([mid_obj] if mid_obj else []) + [in_obj]
            existing_names = {o.name for o in bpy.data.objects} | {c.name for c in bpy.data.curves}
            curve_name = unique_name(f"CABLE_{suffix}", existing_names)
            create_cable_curve(
                collection=legacy_coll,
                cable_name=curve_name,
                controls=controls,
                thickness=settings.thickness,
                bevel_resolution=settings.bevel_resolution,
            )
            created += 1

        if created == 0:
            self.report({"WARNING"}, "Found OUT_ objects, but no matching IN_ objects")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Created {created} cable(s) from named controls")
        return {"FINISHED"}

