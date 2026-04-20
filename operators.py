import math

import bpy

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

from mathutils import Vector


def _ordered_selected_objects(context: bpy.types.Context, order_mode: str) -> list[bpy.types.Object]:
    selected = list(context.selected_objects or [])
    if not selected:
        return []

    if order_mode == "NAME":
        return sorted(selected, key=lambda o: o.name.lower())

    if order_mode == "SELECTION":
        return selected

    # NEAREST: start at active, then greedily chain to nearest remaining.
    active = context.active_object if context.active_object in selected else selected[0]
    remaining = [o for o in selected if o != active]
    ordered = [active]

    current = active
    while remaining:
        current_pos = current.matrix_world.translation
        nearest = min(remaining, key=lambda o: (o.matrix_world.translation - current_pos).length_squared)
        ordered.append(nearest)
        remaining.remove(nearest)
        current = nearest

    return ordered


def _create_controls_for_positions(
    *,
    cable_coll: bpy.types.Collection,
    cable_base_name: str,
    positions: list[Vector],
    empty_size: float,
    parent_objects: list[bpy.types.Object] | None = None,
) -> list[bpy.types.Object]:
    existing_obj_names = {o.name for o in bpy.data.objects}
    controls: list[bpy.types.Object] = []

    for i, pos in enumerate(positions):
        if i == 0:
            suffix = "START"
        elif i == len(positions) - 1:
            suffix = "END"
        else:
            suffix = f"MID_{i:02d}"

        ctrl_name = unique_name(f"CTRL_{cable_base_name}_{suffix}", existing_obj_names | {c.name for c in controls})
        ctrl = make_empty(ctrl_name, pos, empty_size)
        cable_coll.objects.link(ctrl)
        controls.append(ctrl)

        if parent_objects and i < len(parent_objects) and parent_objects[i]:
            parent_keep_world(ctrl, parent_objects[i])

    return controls


class PCG_OT_create_cable_from_selection(bpy.types.Operator):
    bl_idname = "pcg.create_cable_from_selection"
    bl_label = "Create Cable From 2 Selected Objects"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        a, b = ordered_selected_pair(context)
        return a is not None and b is not None and context.mode == "OBJECT"

    def execute(self, context: bpy.types.Context):
        settings = context.scene.pcg_settings
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


class PCG_OT_create_cable_from_object_chain(bpy.types.Operator):
    bl_idname = "pcg.create_cable_from_object_chain"
    bl_label = "Create Cable From Selected Objects (Chain)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.mode == "OBJECT" and len(context.selected_objects or []) >= 2

    def execute(self, context: bpy.types.Context):
        settings = context.scene.pcg_settings
        ordered = _ordered_selected_objects(context, settings.chain_order)
        if len(ordered) < 2:
            self.report({"ERROR"}, "Select 2 or more objects")
            return {"CANCELLED"}

        root = ensure_root_collection(context.scene)
        cable_coll = new_child_collection(root, f"Cable_{settings.cable_name}")

        positions = [o.matrix_world.translation.copy() for o in ordered]
        parent_objs = ordered if settings.parent_chain_controls else None
        controls = _create_controls_for_positions(
            cable_coll=cable_coll,
            cable_base_name=settings.cable_name,
            positions=positions,
            empty_size=settings.empty_size,
            parent_objects=parent_objs,
        )

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
        self.report({"INFO"}, f"Created cable '{curve_obj.name}' through {len(controls)} controls")
        return {"FINISHED"}


class PCG_OT_create_free_cable(bpy.types.Operator):
    bl_idname = "pcg.create_free_cable"
    bl_label = "Create Free Cable (Cursor)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.mode == "OBJECT"

    def execute(self, context: bpy.types.Context):
        settings = context.scene.pcg_settings
        total_controls = max(2, int(settings.free_controls))

        root = ensure_root_collection(context.scene)
        cable_coll = new_child_collection(root, f"Cable_{settings.cable_name}")

        start_pos = context.scene.cursor.location.copy()
        end_pos = start_pos + Vector((settings.free_length, 0.0, 0.0))
        offset_dir = offset_dir_for_slack(start_pos, end_pos)

        positions: list[Vector] = []
        for i in range(total_controls):
            t = 0.0 if total_controls == 1 else i / (total_controls - 1)
            base = start_pos.lerp(end_pos, t)
            offset = offset_dir * (settings.slack * math.sin(math.pi * t))
            positions.append(base + offset)

        controls = _create_controls_for_positions(
            cable_coll=cable_coll,
            cable_base_name=settings.cable_name,
            positions=positions,
            empty_size=settings.empty_size,
            parent_objects=None,
        )

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
        self.report({"INFO"}, f"Created free cable '{curve_obj.name}' with {len(controls)} controls")
        return {"FINISHED"}


class PCG_OT_create_cables_from_out_mid_in(bpy.types.Operator):
    bl_idname = "pcg.create_cables_from_out_mid_in"
    bl_label = "Create Cables From OUT/MID/IN"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context):
        settings = context.scene.pcg_settings
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
