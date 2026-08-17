import os
import tempfile

import bpy

from .utils import is_cable_curve_object, unique_name


CLOTH_ASSET_BLEND_RELATIVE_PATH = os.path.join("assets", "nodes", "geometry_nodes_dynamics_assets.blend")
CLOTH_ASSET_GROUP_NAME = "Cloth Dynamics (Experimental)"
WRAPPER_GROUP_NAME = "PCG Cable Dynamics"
SWAY_GROUP_NAME = "PCG Cable Sway"
DYNAMICS_MODIFIER_NAME = "PCG Dynamics"

TIER_HERO = "HERO"
TIER_BACKGROUND = "BACKGROUND"

# Bumped whenever the wrapper node group's layout changes, so .blend files holding an
# older group get a freshly built one instead of silently reusing an incompatible tree.
WRAPPER_GROUP_VERSION = 4
WRAPPER_VERSION_KEY = "pcg_wrapper_version"

# Upper bound for the XPBD compliance values fed to Cloth Dynamics; see compliance_from().
COMPLIANCE_SCALE = 0.1

# Pin Mode values shared between the node group and PCG_DynamicsSettings.pin_mode.
PIN_MODE_ALL = 0
PIN_MODE_ENDS = 1
PIN_MODE_NONE = 2

# Maps PCG_DynamicsSettings.pin_mode identifiers onto the node group's integer input.
PIN_MODE_VALUES = {"ALL": PIN_MODE_ALL, "ENDS": PIN_MODE_ENDS, "NONE": PIN_MODE_NONE}

COLLIDER_ASSET_GROUP_NAME = "Collider"
COLLIDER_GROUP_NAME = "PCG Cable Collider"
COLLIDER_MODIFIER_NAME = "PCG Collider"
COLLIDER_COLLECTION_NAME = "Cable Colliders"
COLLIDER_GROUP_VERSION = 2
COLLIDER_VERSION_KEY = "pcg_collider_version"


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


def _ensure_bundled_asset(group_name: str) -> bpy.types.NodeTree:
    existing = bpy.data.node_groups.get(group_name)
    if existing is not None:
        return existing

    asset_path = os.path.join(bpy.utils.system_resource("DATAFILES"), CLOTH_ASSET_BLEND_RELATIVE_PATH)
    if not os.path.exists(asset_path):
        raise DynamicsError(
            f"Could not find the bundled '{group_name}' node asset "
            f"(expected at {asset_path}). Dynamics requires Blender 5.2 LTS or newer."
        )

    with bpy.data.libraries.load(asset_path, link=False) as (data_from, data_to):
        if group_name not in data_from.node_groups:
            raise DynamicsError(
                f"The bundled asset file no longer contains a '{group_name}' node group. "
                "This add-on may need updating for this Blender version."
            )
        data_to.node_groups = [group_name]

    return data_to.node_groups[0]


def ensure_cloth_dynamics_asset() -> bpy.types.NodeTree:
    return _ensure_bundled_asset(CLOTH_ASSET_GROUP_NAME)


def get_or_create_collider_group() -> bpy.types.NodeTree:
    existing = bpy.data.node_groups.get(COLLIDER_GROUP_NAME)
    if existing is not None and existing.get(COLLIDER_VERSION_KEY) == COLLIDER_GROUP_VERSION:
        return existing

    collider_asset = _ensure_bundled_asset(COLLIDER_ASSET_GROUP_NAME)
    group_name = unique_name(COLLIDER_GROUP_NAME, {g.name for g in bpy.data.node_groups})
    ng = bpy.data.node_groups.new(group_name, "GeometryNodeTree")
    ng[COLLIDER_VERSION_KEY] = COLLIDER_GROUP_VERSION
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Deforming", in_out="INPUT", socket_type="NodeSocketBool")
    ng.interface.new_socket("Friction", in_out="INPUT", socket_type="NodeSocketFloat")
    ng.interface.new_socket("Margin", in_out="INPUT", socket_type="NodeSocketFloat")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    gin = ng.nodes.new("NodeGroupInput")
    gout = ng.nodes.new("NodeGroupOutput")
    collider = ng.nodes.new("GeometryNodeGroup")
    collider.node_tree = collider_asset
    ng.links.new(gin.outputs["Geometry"], collider.inputs["Geometry"])
    ng.links.new(gin.outputs["Deforming"], collider.inputs["Deforming"])
    ng.links.new(gin.outputs["Friction"], collider.inputs["Friction"])
    ng.links.new(gin.outputs["Margin"], collider.inputs["Margin"])
    ng.links.new(collider.outputs["Geometry"], gout.inputs["Geometry"])
    return ng


def ensure_collider_collection(scene: bpy.types.Scene) -> bpy.types.Collection:
    existing = bpy.data.collections.get(COLLIDER_COLLECTION_NAME)
    if existing is not None:
        if existing.name not in {c.name for c in scene.collection.children}:
            scene.collection.children.link(existing)
        return existing

    collection = bpy.data.collections.new(COLLIDER_COLLECTION_NAME)
    scene.collection.children.link(collection)
    return collection


def make_collider(
    obj: bpy.types.Object,
    *,
    deforming: bool = True,
    friction: float = 0.2,
    margin: float = 0.03,
) -> bool:
    """Set obj up as a collider for simulated cables. Returns True if newly added.

    Re-running updates an existing collider's settings rather than skipping it, so the
    operator doubles as a way to retune margin/friction on already-registered colliders.
    """
    if obj.type != "MESH":
        return False

    mod = obj.modifiers.get(COLLIDER_MODIFIER_NAME)
    newly_added = mod is None
    if newly_added:
        mod = obj.modifiers.new(COLLIDER_MODIFIER_NAME, type="NODES")

    mod.node_group = get_or_create_collider_group()
    _set_modifier_input(mod, "Deforming", deforming)
    _set_modifier_input(mod, "Friction", friction)
    _set_modifier_input(mod, "Margin", margin)
    return newly_added


def get_or_create_sway_group() -> bpy.types.NodeTree:
    """Background-tier group: cheap noise sway, no solver and no collision.

    Unlike the hero group this deforms the cable's *own* geometry, so Blender's native
    curve bevel still applies and no pin anchor or in-group profile is needed.
    """
    existing = bpy.data.node_groups.get(SWAY_GROUP_NAME)
    if existing is not None and existing.get(WRAPPER_VERSION_KEY) == WRAPPER_GROUP_VERSION:
        return existing

    group_name = unique_name(SWAY_GROUP_NAME, {g.name for g in bpy.data.node_groups})
    ng = bpy.data.node_groups.new(group_name, "GeometryNodeTree")
    ng[WRAPPER_VERSION_KEY] = WRAPPER_GROUP_VERSION
    iface = ng.interface
    iface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    iface.new_socket("Sway Amount", in_out="INPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Sway Speed", in_out="INPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Sway Scale", in_out="INPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Resample Count", in_out="INPUT", socket_type="NodeSocketInt")
    iface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    nodes = ng.nodes
    links = ng.links
    gin = nodes.new("NodeGroupInput")
    gout = nodes.new("NodeGroupOutput")

    # Resample so there are enough points to sway smoothly; the control points alone are
    # too sparse to read as movement.
    resample = nodes.new("GeometryNodeResampleCurve")
    links.new(gin.outputs["Geometry"], resample.inputs["Curve"])
    links.new(gin.outputs["Resample Count"], resample.inputs["Count"])

    # Scroll the noise field over time instead of running a solver.
    scene_time = nodes.new("GeometryNodeInputSceneTime")
    time_offset = nodes.new("ShaderNodeMath")
    time_offset.operation = "MULTIPLY"
    links.new(scene_time.outputs["Seconds"], time_offset.inputs[0])
    links.new(gin.outputs["Sway Speed"], time_offset.inputs[1])

    position = nodes.new("GeometryNodeInputPosition")
    scaled_position = nodes.new("ShaderNodeVectorMath")
    scaled_position.operation = "SCALE"
    links.new(position.outputs["Position"], scaled_position.inputs[0])
    links.new(gin.outputs["Sway Scale"], scaled_position.inputs["Scale"])

    drift = nodes.new("ShaderNodeCombineXYZ")
    links.new(time_offset.outputs["Value"], drift.inputs["X"])

    sample_point = nodes.new("ShaderNodeVectorMath")
    sample_point.operation = "ADD"
    links.new(scaled_position.outputs["Vector"], sample_point.inputs[0])
    links.new(drift.outputs["Vector"], sample_point.inputs[1])

    noise = nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions = "3D"
    links.new(sample_point.outputs["Vector"], noise.inputs["Vector"])

    # Noise Color is 0..1 per channel; recentre so the cable sways both ways.
    centred = nodes.new("ShaderNodeVectorMath")
    centred.operation = "SUBTRACT"
    centred.inputs[1].default_value = (0.5, 0.5, 0.5)
    links.new(noise.outputs["Color"], centred.inputs[0])

    # Taper to zero at both ends so a background cable stays attached where it is fixed.
    # The 0..1 position along the cable comes from the point index over the resample count.
    # Two other routes were tried and measured wrong here: Spline Parameter's Factor read as
    # 0 everywhere, and Attribute Domain Size reported a Point Count of 0 for the curve. The
    # resample count is the point count by construction, so use it directly.
    index = nodes.new("GeometryNodeInputIndex")

    last_index = nodes.new("ShaderNodeMath")
    last_index.operation = "SUBTRACT"
    last_index.inputs[1].default_value = 1.0
    links.new(gin.outputs["Resample Count"], last_index.inputs[0])

    factor = nodes.new("ShaderNodeMath")
    factor.operation = "DIVIDE"
    links.new(index.outputs["Index"], factor.inputs[0])
    links.new(last_index.outputs["Value"], factor.inputs[1])

    envelope = nodes.new("ShaderNodeMath")
    envelope.operation = "SINE"
    pi_factor = nodes.new("ShaderNodeMath")
    pi_factor.operation = "MULTIPLY"
    pi_factor.inputs[1].default_value = 3.14159265
    links.new(factor.outputs["Value"], pi_factor.inputs[0])
    links.new(pi_factor.outputs["Value"], envelope.inputs[0])

    amount = nodes.new("ShaderNodeMath")
    amount.operation = "MULTIPLY"
    links.new(envelope.outputs["Value"], amount.inputs[0])
    links.new(gin.outputs["Sway Amount"], amount.inputs[1])

    offset = nodes.new("ShaderNodeVectorMath")
    offset.operation = "SCALE"
    links.new(centred.outputs["Vector"], offset.inputs[0])
    links.new(amount.outputs["Value"], offset.inputs["Scale"])

    set_position = nodes.new("GeometryNodeSetPosition")
    links.new(resample.outputs["Curve"], set_position.inputs["Geometry"])
    links.new(offset.outputs["Vector"], set_position.inputs["Offset"])

    links.new(set_position.outputs["Geometry"], gout.inputs["Geometry"])
    return ng


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
    iface.new_socket("Pin Mode", in_out="INPUT", socket_type="NodeSocketInt")
    iface.new_socket("Colliders", in_out="INPUT", socket_type="NodeSocketCollection")
    iface.new_socket("Thickness", in_out="INPUT", socket_type="NodeSocketFloat")
    iface.new_socket("Profile Resolution", in_out="INPUT", socket_type="NodeSocketInt")
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

    # Pin mask. "All Controls": Index % Segment Divisions == 0 selects exactly the
    # original control points. "Ends Only": just the first and last point, leaving the
    # span between controls free to drape and collide while the controls still shape the
    # cable's rest path. Either way this is a hard 1/0 weight, so pinned controls hold
    # precisely where posed and stay stable when an empty is moved.
    index = nodes.new("GeometryNodeInputIndex")
    index_mod = nodes.new("ShaderNodeMath")
    index_mod.operation = "MODULO"
    links.new(index.outputs["Index"], index_mod.inputs[0])
    links.new(gin.outputs["Segment Divisions"], index_mod.inputs[1])

    on_control = nodes.new("FunctionNodeCompare")
    on_control.data_type = "FLOAT"
    on_control.operation = "EQUAL"
    on_control.inputs[1].default_value = 0.0
    on_control.inputs["Epsilon"].default_value = 0.01
    links.new(index_mod.outputs["Value"], on_control.inputs[0])

    domain_size = nodes.new("GeometryNodeAttributeDomainSize")
    domain_size.component = "MESH"
    links.new(curve_to_mesh.outputs["Mesh"], domain_size.inputs["Geometry"])

    last_index = nodes.new("ShaderNodeMath")
    last_index.operation = "SUBTRACT"
    last_index.inputs[1].default_value = 1.0
    links.new(domain_size.outputs["Point Count"], last_index.inputs[0])

    is_first = nodes.new("FunctionNodeCompare")
    is_first.data_type = "INT"
    is_first.operation = "EQUAL"
    is_first.inputs[1].default_value = 0
    links.new(index.outputs["Index"], is_first.inputs[0])

    is_last = nodes.new("FunctionNodeCompare")
    is_last.data_type = "FLOAT"
    is_last.operation = "EQUAL"
    is_last.inputs["Epsilon"].default_value = 0.01
    links.new(index.outputs["Index"], is_last.inputs[0])
    links.new(last_index.outputs["Value"], is_last.inputs[1])

    on_end = nodes.new("FunctionNodeBooleanMath")
    on_end.operation = "OR"
    links.new(is_first.outputs["Result"], on_end.inputs[0])
    links.new(is_last.outputs["Result"], on_end.inputs[1])

    # Pin Mode: 0 = All Controls, 1 = Ends Only, anything else = None.
    mode_is_all = nodes.new("FunctionNodeCompare")
    mode_is_all.data_type = "INT"
    mode_is_all.operation = "EQUAL"
    mode_is_all.inputs[1].default_value = PIN_MODE_ALL
    links.new(gin.outputs["Pin Mode"], mode_is_all.inputs[0])

    mode_is_ends = nodes.new("FunctionNodeCompare")
    mode_is_ends.data_type = "INT"
    mode_is_ends.operation = "EQUAL"
    mode_is_ends.inputs[1].default_value = PIN_MODE_ENDS
    links.new(gin.outputs["Pin Mode"], mode_is_ends.inputs[0])

    use_all = nodes.new("FunctionNodeBooleanMath")
    use_all.operation = "AND"
    links.new(mode_is_all.outputs["Result"], use_all.inputs[0])
    links.new(on_control.outputs["Result"], use_all.inputs[1])

    use_ends = nodes.new("FunctionNodeBooleanMath")
    use_ends.operation = "AND"
    links.new(mode_is_ends.outputs["Result"], use_ends.inputs[0])
    links.new(on_end.outputs["Boolean"], use_ends.inputs[1])

    is_pinned = nodes.new("FunctionNodeBooleanMath")
    is_pinned.operation = "OR"
    links.new(use_all.outputs["Boolean"], is_pinned.inputs[0])
    links.new(use_ends.outputs["Boolean"], is_pinned.inputs[1])

    cloth_node = nodes.new("GeometryNodeGroup")
    cloth_node.node_tree = cloth_asset
    links.new(curve_to_mesh.outputs["Mesh"], cloth_node.inputs["Geometry"])
    links.new(is_pinned.outputs["Boolean"], cloth_node.inputs["Pin Group"])
    links.new(gin.outputs["Colliders"], cloth_node.inputs["Effectors Collection"])
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

    # Convert the simulated point/edge mesh back to a curve, then bevel it here rather
    # than relying on the object's own Bevel Depth. Blender only applies a curve object's
    # native bevel to geometry originating from its own curve data, and this cable is
    # rebuilt from the pin anchor object, so the native bevel is dropped - leaving the
    # cable rendering as a zero-thickness line. Beveling in the tree restores the tube.
    mesh_to_curve = nodes.new("GeometryNodeMeshToCurve")
    links.new(cloth_node.outputs["Geometry"], mesh_to_curve.inputs["Mesh"])

    # Blender's bevel_resolution counts subdivisions per quarter turn, so a full profile
    # circle has (resolution + 1) * 4 segments.
    profile_segments = nodes.new("ShaderNodeMath")
    profile_segments.operation = "ADD"
    profile_segments.inputs[1].default_value = 1.0
    links.new(gin.outputs["Profile Resolution"], profile_segments.inputs[0])

    profile_resolution = nodes.new("ShaderNodeMath")
    profile_resolution.operation = "MULTIPLY"
    profile_resolution.inputs[1].default_value = 4.0
    links.new(profile_segments.outputs["Value"], profile_resolution.inputs[0])

    profile = nodes.new("GeometryNodeCurvePrimitiveCircle")
    profile.mode = "RADIUS"
    links.new(profile_resolution.outputs["Value"], profile.inputs["Resolution"])
    links.new(gin.outputs["Thickness"], profile.inputs["Radius"])

    tube = nodes.new("GeometryNodeCurveToMesh")
    tube.inputs["Fill Caps"].default_value = True
    links.new(mesh_to_curve.outputs["Curve"], tube.inputs["Curve"])
    links.new(profile.outputs["Curve"], tube.inputs["Profile Curve"])

    links.new(tube.outputs["Mesh"], gout.inputs["Geometry"])
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


def resolve_alembic_directory(settings) -> tuple[str, str | None]:
    """Resolve the export folder, returning (absolute_path, warning_or_None).

    Blender's "//" prefix means "next to the .blend", but it resolves to an empty string
    while the file is unsaved, so fall back to the temp folder rather than writing nowhere.
    """
    raw = (settings.alembic_directory or "").strip()
    if raw:
        resolved = bpy.path.abspath(raw)
        if resolved:
            return resolved, None

    if bpy.data.is_saved:
        return os.path.dirname(bpy.data.filepath), None

    fallback = bpy.app.tempdir or tempfile.gettempdir()
    return fallback, (
        "This .blend has not been saved, so the cable was exported to a temporary folder "
        f"({fallback}). Save the .blend first to keep exports beside your project"
    )


def bake_cable_to_mesh(
    cable_obj: bpy.types.Object,
    frame_start: int,
    frame_end: int,
    *,
    depsgraph_getter=None,
    frame_setter=None,
) -> tuple[bpy.types.Object, int]:
    """Snapshot the simulated cable across a frame range into a shape-keyed mesh.

    Returns (baked_object, frame_count). Kept self-contained in the .blend, so the result
    survives without the live setup or any external cache file.
    """
    get_depsgraph = depsgraph_getter or bpy.context.evaluated_depsgraph_get
    set_frame = frame_setter or bpy.context.scene.frame_set

    def evaluated_vertices() -> list:
        evaluated = cable_obj.evaluated_get(get_depsgraph())
        mesh = evaluated.to_mesh()
        if mesh is None:
            evaluated.to_mesh_clear()
            return []
        coordinates = [vertex.co.copy() for vertex in mesh.vertices]
        evaluated.to_mesh_clear()
        return coordinates

    set_frame(frame_start)
    first_frame = evaluated_vertices()
    if not first_frame:
        raise DynamicsError("The cable produced no geometry to bake.")

    baked_mesh = bpy.data.meshes.new(unique_name(f"BAKED_{cable_obj.name}", {m.name for m in bpy.data.meshes}))
    evaluated = cable_obj.evaluated_get(get_depsgraph())
    source_mesh = evaluated.to_mesh()
    baked_mesh.from_pydata(
        [tuple(v.co) for v in source_mesh.vertices],
        [tuple(e.vertices) for e in source_mesh.edges],
        [tuple(p.vertices) for p in source_mesh.polygons],
    )
    evaluated.to_mesh_clear()
    baked_mesh.update()

    baked_obj = bpy.data.objects.new(baked_mesh.name, baked_mesh)
    for collection in cable_obj.users_collection or (bpy.context.scene.collection,):
        collection.objects.link(baked_obj)

    baked_obj.shape_key_add(name="Basis", from_mix=False)
    vertex_count = len(baked_mesh.vertices)
    baked = 0

    for frame in range(frame_start, frame_end + 1):
        set_frame(frame)
        coordinates = evaluated_vertices()
        # A settings change mid-bake would alter the vertex count and desynchronise the
        # shape keys, so stop rather than write a corrupt result.
        if len(coordinates) != vertex_count:
            raise DynamicsError(
                f"The cable's geometry changed at frame {frame} "
                f"({len(coordinates)} points, expected {vertex_count}); bake stopped."
            )

        key = baked_obj.shape_key_add(name=f"frame_{frame:04d}", from_mix=False)
        for index, coordinate in enumerate(coordinates):
            key.data[index].co = coordinate

        # Hold this frame's shape at full strength only on its own frame.
        key.value = 0.0
        key.keyframe_insert("value", frame=frame - 1)
        key.value = 1.0
        key.keyframe_insert("value", frame=frame)
        key.value = 0.0
        key.keyframe_insert("value", frame=frame + 1)
        baked += 1

    return baked_obj, baked


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

    # Adopt the cable's existing bevel settings so enabling dynamics does not change how
    # thick it looks; from here on the panel's Thickness drives both.
    settings.thickness = cable_obj.data.bevel_depth
    settings.profile_resolution = cable_obj.data.bevel_resolution

    settings.anchor_object = anchor_obj

    mod = cable_obj.modifiers.new(DYNAMICS_MODIFIER_NAME, type="NODES")
    # Always build the hero group first so the anchor input can be set, then let
    # sync_dynamics_settings swap in the background group if that tier is selected.
    mod.node_group = wrapper_group
    _set_modifier_input(mod, "Pin Anchors", anchor_obj)

    # If colliders have already been set up in this file, use them by default rather than
    # leaving the cable silently non-colliding until the field is filled in by hand.
    if settings.collision_collection is None:
        existing_colliders = bpy.data.collections.get(COLLIDER_COLLECTION_NAME)
        if existing_colliders is not None:
            settings.collision_collection = existing_colliders

    sync_dynamics_settings(cable_obj, settings)


def disable_dynamics(cable_obj: bpy.types.Object) -> None:
    mod = cable_obj.modifiers.get(DYNAMICS_MODIFIER_NAME)
    if mod is None:
        return

    # Read from the settings rather than the modifier: the background tier's group has no
    # Pin Anchors socket, so the modifier cannot be relied on to still hold it.
    settings = cable_obj.pcg_dynamics
    anchor_obj = settings.anchor_object
    if anchor_obj is None:
        try:
            anchor_obj = _get_modifier_input(mod, "Pin Anchors")
        except KeyError:
            pass

    cable_obj.modifiers.remove(mod)
    settings.anchor_object = None

    if anchor_obj is not None:
        anchor_mesh = anchor_obj.data
        bpy.data.objects.remove(anchor_obj, do_unlink=True)
        if anchor_mesh is not None and anchor_mesh.users == 0:
            bpy.data.meshes.remove(anchor_mesh)


def node_group_for_tier(tier: str) -> bpy.types.NodeTree:
    if tier == TIER_BACKGROUND:
        return get_or_create_sway_group()
    return get_or_create_wrapper_group()


def sync_dynamics_settings(cable_obj: bpy.types.Object, settings) -> None:
    mod = cable_obj.modifiers.get(DYNAMICS_MODIFIER_NAME)
    if mod is None:
        return

    # Switching tier swaps the node group in place, restoring the anchor from the settings
    # so the hero setup survives a round trip through the background tier.
    wanted = node_group_for_tier(settings.tier)
    if mod.node_group is not wanted:
        mod.node_group = wanted
    if settings.tier != TIER_BACKGROUND and settings.anchor_object is not None:
        _set_modifier_input(mod, "Pin Anchors", settings.anchor_object)

    if settings.tier == TIER_BACKGROUND:
        _set_modifier_input(mod, "Sway Amount", settings.sway_amount)
        _set_modifier_input(mod, "Sway Speed", settings.sway_speed)
        _set_modifier_input(mod, "Sway Scale", settings.sway_scale)
        _set_modifier_input(mod, "Resample Count", settings.sway_resample)
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
    _set_modifier_input(mod, "Pin Mode", PIN_MODE_VALUES.get(settings.pin_mode, PIN_MODE_ALL))
    _set_modifier_input(mod, "Colliders", settings.collision_collection)
    _set_modifier_input(mod, "Thickness", settings.thickness)
    _set_modifier_input(mod, "Profile Resolution", settings.profile_resolution)
