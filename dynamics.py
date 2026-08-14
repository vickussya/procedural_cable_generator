import os

import bpy

from .utils import is_cable_curve_object, unique_name


CLOTH_ASSET_BLEND_RELATIVE_PATH = os.path.join("assets", "nodes", "geometry_nodes_dynamics_assets.blend")
CLOTH_ASSET_GROUP_NAME = "Cloth Dynamics (Experimental)"
WRAPPER_GROUP_NAME = "PCG Cable Dynamics"
DYNAMICS_MODIFIER_NAME = "PCG Dynamics"

# Bumped whenever the wrapper node group's layout changes, so .blend files holding an
# older group get a freshly built one instead of silently reusing an incompatible tree.
WRAPPER_GROUP_VERSION = 2
WRAPPER_VERSION_KEY = "pcg_wrapper_version"

# Upper bound for the XPBD compliance values fed to Cloth Dynamics; see compliance_from().
COMPLIANCE_SCALE = 0.1


class DynamicsError(Exception):
    """Raised for recoverable dynamics setup failures; callers turn this into self.report()."""


def _input_identifier(node_group: bpy.types.NodeTree, socket_name: str) -> str:
    for item in node_group.interface.items_tree:
        if item.in_out == "INPUT" and item.name == socket_name:
            return item.identifier
    raise KeyError(f"No input socket named {socket_name!r} on node group {node_group.name!r}")


def _set_modifier_input(mod: bpy.types.NodesModifier, socket_name: str, value) -> None:
    identifier = _input_identifier(mod.node_group, socket_name)
    getattr(mod.properties.inputs, identifier).value = value


def _get_modifier_input(mod: bpy.types.NodesModifier, socket_name: str):
    identifier = _input_identifier(mod.node_group, socket_name)
    return getattr(mod.properties.inputs, identifier).value


def ensure_cloth_dynamics_asset() -> bpy.types.NodeTree:
    existing = bpy.data.node_groups.get(CLOTH_ASSET_GROUP_NAME)
    if existing is not None:
        return existing

    asset_path = os.path.join(bpy.utils.system_resource("DATAFILES"), CLOTH_ASSET_BLEND_RELATIVE_PATH)
    if not os.path.exists(asset_path):
        raise DynamicsError(
            "Could not find the bundled 'Cloth Dynamics (Experimental)' node asset "
            f"(expected at {asset_path}). Dynamics requires Blender 5.2 LTS or newer."
        )

    with bpy.data.libraries.load(asset_path, link=False) as (data_from, data_to):
        if CLOTH_ASSET_GROUP_NAME not in data_from.node_groups:
            raise DynamicsError(
                f"The bundled asset file no longer contains a '{CLOTH_ASSET_GROUP_NAME}' node group. "
                "This add-on may need updating for this Blender version."
            )
        data_to.node_groups = [CLOTH_ASSET_GROUP_NAME]

    return data_to.node_groups[0]


def get_or_create_wrapper_group() -> bpy.types.NodeTree:
    existing = bpy.data.node_groups.get(WRAPPER_GROUP_NAME)
    if existing is not None and existing.get(WRAPPER_VERSION_KEY) == WRAPPER_GROUP_VERSION:
        return existing
    cloth_asset = ensure_cloth_dynamics_asset()
    return _build_wrapper_node_group(cloth_asset)


def _build_wrapper_node_group(cloth_asset: bpy.types.NodeTree) -> bpy.types.NodeTree:
    group_name = unique_name(WRAPPER_GROUP_NAME, {g.name for g in bpy.data.node_groups})
    ng = bpy.data.node_groups.new(group_name, "GeometryNodeTree")
    ng[WRAPPER_VERSION_KEY] = WRAPPER_GROUP_VERSION
    iface = ng.interface
    iface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    iface.new_socket("Pin Anchors", in_out="INPUT", socket_type="NodeSocketObject")
    iface.new_socket("Mass", in_out="INPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Stiffness", in_out="INPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Bend", in_out="INPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Damping", in_out="INPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Friction", in_out="INPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Collision Radius", in_out="INPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Substeps", in_out="INPUT", socket_type="NodeSocketInt")
    iface.new_socket("Constraint Steps", in_out="INPUT", socket_type="NodeSocketInt")
    iface.new_socket("Segment Divisions", in_out="INPUT", socket_type="NodeSocketInt")
    iface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    iface.new_socket("Residual Error", in_out="OUTPUT", socket_type="NodeSocketFloat")

    nodes = ng.nodes
    links = ng.links

    gin = nodes.new("NodeGroupInput")
    gout = nodes.new("NodeGroupOutput")

    # The simulated cable is built from the "Pin Anchors" object: a polyline with exactly
    # one vertex per CTRL_* empty, each vertex following its empty via a Hook modifier
    # (see _create_pin_anchor_object). Driving the sim from that polyline - rather than
    # from the cable curve - is what makes pinning exact: after subdividing each segment
    # into N parts, the original controls land on known indices (0, N, 2N, ...), so they
    # can be pinned at full strength by index instead of by world-space proximity.
    obj_info = nodes.new("GeometryNodeObjectInfo")
    obj_info.transform_space = "RELATIVE"
    links.new(gin.outputs["Pin Anchors"], obj_info.inputs["Object"])

    anchors_to_curve = nodes.new("GeometryNodeMeshToCurve")
    links.new(obj_info.outputs["Geometry"], anchors_to_curve.inputs["Mesh"])

    # Catmull-Rom interpolates smoothly *through* every control, so the rest shape stays
    # curved rather than becoming a faceted polyline.
    smooth_type = nodes.new("GeometryNodeCurveSplineType")
    smooth_type.spline_type = "CATMULL_ROM"
    links.new(anchors_to_curve.outputs["Curve"], smooth_type.inputs["Curve"])

    cuts = nodes.new("ShaderNodeMath")
    cuts.operation = "SUBTRACT"
    cuts.inputs[1].default_value = 1.0
    links.new(gin.outputs["Segment Divisions"], cuts.inputs[0])

    subdivide = nodes.new("GeometryNodeSubdivideCurve")
    links.new(smooth_type.outputs["Curve"], subdivide.inputs["Curve"])
    links.new(cuts.outputs["Value"], subdivide.inputs["Cuts"])

    poly_type = nodes.new("GeometryNodeCurveSplineType")
    poly_type.spline_type = "POLY"
    links.new(subdivide.outputs["Curve"], poly_type.inputs["Curve"])

    curve_to_mesh = nodes.new("GeometryNodeCurveToMesh")
    links.new(poly_type.outputs["Curve"], curve_to_mesh.inputs["Curve"])

    # Pin mask: Index % Segment Divisions == 0 selects exactly the original control
    # points. This is a hard 1/0 weight, so pinned controls hold precisely where posed
    # and stay stable when an empty is moved.
    index = nodes.new("GeometryNodeInputIndex")
    index_mod = nodes.new("ShaderNodeMath")
    index_mod.operation = "MODULO"
    links.new(index.outputs["Index"], index_mod.inputs[0])
    links.new(gin.outputs["Segment Divisions"], index_mod.inputs[1])

    is_pinned = nodes.new("FunctionNodeCompare")
    is_pinned.data_type = "FLOAT"
    is_pinned.operation = "EQUAL"
    is_pinned.inputs[1].default_value = 0.0
    is_pinned.inputs["Epsilon"].default_value = 0.01
    links.new(index_mod.outputs["Value"], is_pinned.inputs[0])

    cloth_node = nodes.new("GeometryNodeGroup")
    cloth_node.node_tree = cloth_asset
    links.new(curve_to_mesh.outputs["Mesh"], cloth_node.inputs["Geometry"])
    links.new(is_pinned.outputs["Result"], cloth_node.inputs["Pin Group"])
    links.new(gin.outputs["Mass"], cloth_node.inputs["Mass"])
    links.new(gin.outputs["Friction"], cloth_node.inputs["Friction"])
    links.new(gin.outputs["Collision Radius"], cloth_node.inputs["Collision Radius"])
    links.new(gin.outputs["Substeps"], cloth_node.inputs["Substeps"])
    links.new(gin.outputs["Constraint Steps"], cloth_node.inputs["Constraint Steps"])
    links.new(gin.outputs["Damping"], cloth_node.inputs["Linear Damping"])

    # Cloth Dynamics exposes Stretchiness/Bendiness as XPBD *compliance* values, where 0
    # is rigid. Measured behavior: compliance up to ~0.06 keeps a cable clean, while ~0.26
    # collapses it into hard kinks. A linear 1-slider mapping therefore spends most of the
    # slider in unusable territory. Remapping as (1 - slider)^3 * COMPLIANCE_SCALE keeps
    # the whole slider inside the usable band and gives finer control near the stiff end,
    # which is where cables actually live.
    def compliance_from(socket_name: str, target_input: str) -> None:
        softness = nodes.new("ShaderNodeMath")
        softness.operation = "SUBTRACT"
        softness.inputs[0].default_value = 1.0
        links.new(gin.outputs[socket_name], softness.inputs[1])

        curved = nodes.new("ShaderNodeMath")
        curved.operation = "POWER"
        curved.inputs[1].default_value = 3.0
        links.new(softness.outputs["Value"], curved.inputs[0])

        scaled = nodes.new("ShaderNodeMath")
        scaled.operation = "MULTIPLY"
        scaled.inputs[1].default_value = COMPLIANCE_SCALE
        links.new(curved.outputs["Value"], scaled.inputs[0])
        links.new(scaled.outputs["Value"], cloth_node.inputs[target_input])

    compliance_from("Stiffness", "Stretchiness")
    compliance_from("Bend", "Bendiness")

    # Convert the simulated point/edge mesh back to a curve so the object's own
    # Bevel Depth/Resolution (set by utils.create_cable_curve) still render the tube -
    # no separate profile geometry or per-frame Python read-back is needed for display.
    mesh_to_curve = nodes.new("GeometryNodeMeshToCurve")
    links.new(cloth_node.outputs["Geometry"], mesh_to_curve.inputs["Mesh"])

    links.new(mesh_to_curve.outputs["Curve"], gout.inputs["Geometry"])
    links.new(cloth_node.outputs["Residual Error"], gout.inputs["Residual Error"])

    return ng


def get_cable_controls(cable_obj: bpy.types.Object) -> list[bpy.types.Object | None]:
    curve_data = cable_obj.data
    spline = curve_data.splines[0]
    anim = curve_data.animation_data
    controls: list[bpy.types.Object | None] = []

    for i in range(len(spline.bezier_points)):
        target = None
        if anim is not None:
            path = f"splines[0].bezier_points[{i}].co"
            for fcurve in anim.drivers:
                if fcurve.data_path == path and fcurve.driver.variables:
                    targets = fcurve.driver.variables[0].targets
                    if targets:
                        target = targets[0].id
                    break
        controls.append(target)

    return controls


def _create_pin_anchor_object(cable_obj: bpy.types.Object, controls: list[bpy.types.Object]) -> bpy.types.Object:
    positions = [c.matrix_world.translation.copy() for c in controls]

    mesh_name = unique_name(f"PINS_{cable_obj.name}", {m.name for m in bpy.data.meshes})
    mesh = bpy.data.meshes.new(mesh_name)
    # Edges between consecutive controls make this a polyline, which the node group
    # converts to a curve and subdivides to build the simulated cable.
    edges = [(i, i + 1) for i in range(len(positions) - 1)]
    mesh.from_pydata([tuple(p) for p in positions], edges, [])
    mesh.update()

    anchor_obj = bpy.data.objects.new(mesh_name, mesh)
    target_collections = cable_obj.users_collection or (bpy.context.scene.collection,)
    for collection in target_collections:
        collection.objects.link(anchor_obj)
    anchor_obj.hide_viewport = True
    anchor_obj.hide_render = True

    for i, ctrl in enumerate(controls):
        vertex_group = anchor_obj.vertex_groups.new(name=f"pin_{i:02d}")
        vertex_group.add([i], 1.0, "REPLACE")
        hook = anchor_obj.modifiers.new(f"Hook_{i:02d}", type="HOOK")
        hook.object = ctrl
        hook.vertex_group = vertex_group.name
        # Hook modifiers created via Python default matrix_inverse to identity, which
        # would double-apply the target's transform. Ctrl+H in the UI sets this
        # automatically; scripted creation must set it explicitly.
        hook.matrix_inverse = ctrl.matrix_world.inverted() @ anchor_obj.matrix_world

    return anchor_obj


def resolve_cable_for_object(obj: bpy.types.Object | None) -> bpy.types.Object | None:
    """Return the cable curve for obj, which may be the curve itself or one of its controls."""
    if obj is None:
        return None
    if is_cable_curve_object(obj):
        return obj

    # Control empties are linked into the same collection as their cable curve, so the
    # search stays local rather than scanning the whole file on every panel redraw.
    for collection in obj.users_collection:
        for candidate in collection.objects:
            if is_cable_curve_object(candidate) and obj in get_cable_controls(candidate):
                return candidate
    return None


def is_dynamics_enabled(cable_obj: bpy.types.Object | None) -> bool:
    return cable_obj is not None and cable_obj.modifiers.get(DYNAMICS_MODIFIER_NAME) is not None


def enable_dynamics(cable_obj: bpy.types.Object, settings) -> None:
    if not is_cable_curve_object(cable_obj):
        raise DynamicsError("Active object is not a Procedural Cable Generator cable curve.")
    if is_dynamics_enabled(cable_obj):
        raise DynamicsError("Dynamics is already enabled on this cable.")

    controls = get_cable_controls(cable_obj)
    if not controls or any(c is None for c in controls):
        raise DynamicsError(
            "This cable's points aren't all driven by CTRL_* control empties, so it can't be made dynamic."
        )

    wrapper_group = get_or_create_wrapper_group()
    anchor_obj = _create_pin_anchor_object(cable_obj, controls)

    mod = cable_obj.modifiers.new(DYNAMICS_MODIFIER_NAME, type="NODES")
    mod.node_group = wrapper_group
    _set_modifier_input(mod, "Pin Anchors", anchor_obj)
    sync_dynamics_settings(cable_obj, settings)


def disable_dynamics(cable_obj: bpy.types.Object) -> None:
    mod = cable_obj.modifiers.get(DYNAMICS_MODIFIER_NAME)
    if mod is None:
        return

    anchor_obj = None
    try:
        anchor_obj = _get_modifier_input(mod, "Pin Anchors")
    except KeyError:
        pass

    cable_obj.modifiers.remove(mod)

    if anchor_obj is not None:
        anchor_mesh = anchor_obj.data
        bpy.data.objects.remove(anchor_obj, do_unlink=True)
        if anchor_mesh is not None and anchor_mesh.users == 0:
            bpy.data.meshes.remove(anchor_mesh)


def sync_dynamics_settings(cable_obj: bpy.types.Object, settings) -> None:
    mod = cable_obj.modifiers.get(DYNAMICS_MODIFIER_NAME)
    if mod is None:
        return
    _set_modifier_input(mod, "Mass", settings.mass)
    _set_modifier_input(mod, "Stiffness", settings.stiffness)
    _set_modifier_input(mod, "Bend", settings.bend)
    _set_modifier_input(mod, "Damping", settings.damping)
    _set_modifier_input(mod, "Friction", settings.friction)
    _set_modifier_input(mod, "Collision Radius", settings.collision_radius)
    _set_modifier_input(mod, "Substeps", settings.substeps)
    _set_modifier_input(mod, "Constraint Steps", settings.constraint_steps)
    _set_modifier_input(mod, "Segment Divisions", settings.segment_divisions)
