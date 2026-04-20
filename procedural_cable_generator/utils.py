import math

import bpy
from mathutils import Matrix, Vector


ROOT_COLLECTION_NAME = "Procedural Cables"


def unique_name(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    for i in range(1, 10_000):
        candidate = f"{base}.{i:03d}"
        if candidate not in existing:
            return candidate
    return f"{base}.{math.floor(10_000 * math.pi)}"


def ensure_root_collection(scene: bpy.types.Scene) -> bpy.types.Collection:
    existing = bpy.data.collections.get(ROOT_COLLECTION_NAME)
    if existing:
        if existing.name not in {c.name for c in scene.collection.children}:
            scene.collection.children.link(existing)
        return existing

    root = bpy.data.collections.new(ROOT_COLLECTION_NAME)
    scene.collection.children.link(root)
    return root


def new_child_collection(parent: bpy.types.Collection, base_name: str) -> bpy.types.Collection:
    name = unique_name(base_name, {c.name for c in bpy.data.collections})
    child = bpy.data.collections.new(name)
    parent.children.link(child)
    return child


def ordered_selected_pair(context: bpy.types.Context):
    selected = list(context.selected_objects or [])
    if len(selected) != 2:
        return None, None
    active = context.active_object if context.active_object in selected else selected[0]
    other = selected[1] if selected[0] == active else selected[0]
    return active, other


def offset_dir_for_slack(start: Vector, end: Vector) -> Vector:
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


def make_empty(name: str, location_world: Vector, empty_size: float) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = empty_size
    obj.matrix_world = Matrix.Translation(location_world)
    return obj


def parent_keep_world(child: bpy.types.Object, parent: bpy.types.Object) -> None:
    world = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    child.matrix_world = world


def add_point_world_location_driver(
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


def create_cable_curve(
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
        add_point_world_location_driver(bp, ctrl)

    curve_obj = bpy.data.objects.new(cable_name, curve_data)
    curve_obj.matrix_world = Matrix.Identity(4)
    collection.objects.link(curve_obj)
    return curve_obj

