bl_info = {
    "name": "Procedural Cable Generator",
    "author": "procedural_cable_generator contributors",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Cable",
    "description": "Generate editable cable curves driven by control empties.",
    "category": "Object",
}

import math

import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, PointerProperty, StringProperty
from mathutils import Matrix, Vector


ROOT_COLLECTION_NAME = "Procedural Cables"


def _unique_name(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    for i in range(1, 10_000):
        candidate = f"{base}.{i:03d}"
        if candidate not in existing:
            return candidate
    return f"{base}.{math.floor(10_000 * math.pi)}"


def _ensure_root_collection(scene: bpy.types.Scene) -> bpy.types.Collection:
    existing = bpy.data.collections.get(ROOT_COLLECTION_NAME)
    if existing:
        if existing.name not in {c.name for c in scene.collection.children}:
            scene.collection.children.link(existing)
        return existing

    root = bpy.data.collections.new(ROOT_COLLECTION_NAME)
    scene.collection.children.link(root)
    return root


def _new_child_collection(parent: bpy.types.Collection, base_name: str) -> bpy.types.Collection:
    name = _unique_name(base_name, {c.name for c in bpy.data.collections})
    child = bpy.data.collections.new(name)
    parent.children.link(child)
    return child


def _ordered_selected_pair(context: bpy.types.Context):
    selected = list(context.selected_objects or [])
    if len(selected) != 2:
        return None, None
    active = context.active_object if context.active_object in selected else selected[0]
    other = selected[1] if selected[0] == active else selected[0]
    return active, other


def _offset_dir_for_slack(start: Vector, end: Vector) -> Vector:
    line = end - start
    if line.length < 1e-8:
        return Vector((0.0, 0.0, 1.0))

    direction = line.normalized()
    up = Vector((0.0, 0.0, 1.0))
    perp = up - direction * up.dot(direction)

    if perp.length < 1e-6:
        up = Vector((1.0, 0.0, 0.0))
        perp = up - direction * up.dot(direction)

    if perp.length < 1e-6:
        return Vector((0.0, 0.0, 1.0))

    return perp.normalized()


def _make_empty(name: str, location_world: Vector, empty_size: float) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = empty_size
    obj.matrix_world = Matrix.Translation(location_world)
    return obj


def _parent_keep_world(child: bpy.types.Object, parent: bpy.types.Object) -> None:
    world = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    child.matrix_world = world


def _add_point_world_location_driver(
    bezier_point: bpy.types.BezierSplinePoint,
    empty: bpy.types.Object,
) -> None:
    for axis, transform_type, var_name in (
        (0, "LOC_X", "vx"),
        (1, "LOC_Y", "vy"),
        (2, "LOC_Z", "vz"),
    ):
        fcurve = bezier_point.driver_add("co", axis)
        driver = fcurve.driver
        driver.type = "SCRIPTED"
        driver.variables.clear()

        var = driver.variables.new()
        var.name = var_name
        var.type = "TRANSFORMS"
        target = var.targets[0]
        target.id = empty
        target.transform_type = transform_type
        target.transform_space = "WORLD_SPACE"

        driver.expression = var_name


def _create_cable_curve(
    *,
    collection: bpy.types.Collection,
    cable_name: str,
    controls: list[bpy.types.Object],
    thickness: float,
    bevel_resolution: int,
) -> bpy.types.Object:
    curve_data = bpy.data.curves.new(cable_name, type="CURVE")
    curve_data.dimensions = "3D"
    curve_data.fill_mode = "FULL"
    curve_data.use_fill_caps = True
    curve_data.bevel_depth = thickness
    curve_data.bevel_resolution = bevel_resolution

    spline = curve_data.splines.new(type="BEZIER")
    spline.bezier_points.add(max(0, len(controls) - 1))

    for i, ctrl in enumerate(controls):
        bp = spline.bezier_points[i]
        bp.co = ctrl.matrix_world.translation
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
        _add_point_world_location_driver(bp, ctrl)

    curve_obj = bpy.data.objects.new(cable_name, curve_data)
    curve_obj.matrix_world = Matrix.Identity(4)
    collection.objects.link(curve_obj)
    return curve_obj


class PCG_Settings(bpy.types.PropertyGroup):
    cable_name: StringProperty(
        name="Cable Name",
        default="Cable",
        description="Name for the generated cable setup",
    )

    thickness: FloatProperty(
        name="Thickness",
        default=0.008,
        min=0.0,
        soft_max=0.2,
        description="Curve bevel depth",
        subtype="DISTANCE",
        unit="LENGTH",
    )

    bevel_resolution: IntProperty(
        name="Bevel Resolution",
        default=3,
        min=0,
        max=12,
        description="Curve bevel resolution",
    )

    middle_controls: IntProperty(
        name="Middle Controls",
        default=1,
        min=0,
        max=20,
        description="Number of middle control empties between start and end",
    )

    slack: FloatProperty(
        name="Slack",
        default=0.0,
        soft_min=-2.0,
        soft_max=2.0,
        description="Offsets the middle controls along an up-ish direction (use negative for sag)",
        subtype="DISTANCE",
        unit="LENGTH",
    )

    empty_size: FloatProperty(
        name="Control Size",
        default=0.12,
        min=0.01,
        soft_max=2.0,
        description="Viewport size of generated control empties",
        subtype="DISTANCE",
        unit="LENGTH",
    )

    parent_end_controls: BoolProperty(
        name="Parent End Controls",
        default=True,
        description="Parent start/end controls to the selected objects so the cable follows when they move",
    )

    show_legacy: BoolProperty(
        name="Show Legacy Tools",
        default=False,
    )

    legacy_out_prefix: StringProperty(name="OUT Prefix", default="OUT_")
    legacy_mid_prefix: StringProperty(name="MID Prefix", default="MID_")
    legacy_in_prefix: StringProperty(name="IN Prefix", default="IN_")


class PCG_OT_create_cable_from_selection(bpy.types.Operator):
    bl_idname = "pcg.create_cable_from_selection"
    bl_label = "Create Cable From Selection"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        a, b = _ordered_selected_pair(context)
        return a is not None and b is not None and context.mode == "OBJECT"

    def execute(self, context: bpy.types.Context):
        settings: PCG_Settings = context.scene.pcg_settings
        start_obj, end_obj = _ordered_selected_pair(context)
        if not start_obj or not end_obj:
            self.report({"ERROR"}, "Select exactly two objects (active object is Start)")
            return {"CANCELLED"}

        root = _ensure_root_collection(context.scene)
        cable_coll = _new_child_collection(root, f"Cable_{settings.cable_name}")

        start_pos = start_obj.matrix_world.translation.copy()
        end_pos = end_obj.matrix_world.translation.copy()

        ctrl_names = {o.name for o in bpy.data.objects}
        start_empty = _make_empty(
            _unique_name(f"CTRL_{settings.cable_name}_START", ctrl_names),
            start_pos,
            settings.empty_size,
        )
        end_empty = _make_empty(
            _unique_name(f"CTRL_{settings.cable_name}_END", ctrl_names | {start_empty.name}),
            end_pos,
            settings.empty_size,
        )

        if settings.parent_end_controls:
            _parent_keep_world(start_empty, start_obj)
            _parent_keep_world(end_empty, end_obj)

        cable_coll.objects.link(start_empty)
        cable_coll.objects.link(end_empty)

        offset_dir = _offset_dir_for_slack(start_pos, end_pos)
        controls: list[bpy.types.Object] = [start_empty]

        for i in range(settings.middle_controls):
            t = (i + 1) / (settings.middle_controls + 1)
            base = start_pos.lerp(end_pos, t)
            offset = offset_dir * (settings.slack * math.sin(math.pi * t))
            mid_pos = base + offset
            mid_name = _unique_name(
                f"CTRL_{settings.cable_name}_MID_{i + 1:02d}",
                {o.name for o in bpy.data.objects} | {c.name for c in controls} | {end_empty.name},
            )
            mid_empty = _make_empty(mid_name, mid_pos, settings.empty_size)
            cable_coll.objects.link(mid_empty)
            controls.append(mid_empty)

        controls.append(end_empty)

        curve_name = _unique_name(f"CABLE_{settings.cable_name}", {o.name for o in bpy.data.objects})
        curve_obj = _create_cable_curve(
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

        root = _ensure_root_collection(context.scene)
        legacy_coll = _new_child_collection(root, "Legacy_OUT_MID_IN")

        created = 0
        for out_obj in outs:
            suffix = out_obj.name[len(out_prefix) :]
            in_obj = bpy.data.objects.get(f"{in_prefix}{suffix}")
            if not in_obj:
                continue
            mid_obj = bpy.data.objects.get(f"{mid_prefix}{suffix}")

            controls = [out_obj] + ([mid_obj] if mid_obj else []) + [in_obj]
            curve_name = _unique_name(f"CABLE_{suffix}", {o.name for o in bpy.data.objects})
            _create_cable_curve(
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


_CLASSES = (
    PCG_Settings,
    PCG_OT_create_cable_from_selection,
    PCG_OT_create_cables_from_out_mid_in,
    PCG_PT_cable_panel,
)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.pcg_settings = PointerProperty(type=PCG_Settings)


def unregister():
    del bpy.types.Scene.pcg_settings
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
