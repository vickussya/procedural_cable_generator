import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

from . import dynamics


# Ready-made coil shapes. Real coiled cable nests outward rather than stacking into a
# slinky, so these mostly keep pitch low and grow the radius instead.
_COIL_PRESETS = {
    "GROUND": {
        "coil_radius": 0.28,
        "coil_radius_end": 0.46,
        "coil_turns": 3.5,
        "coil_pitch": 0.012,
        "coil_controls_per_turn": 8,
        "coil_randomness": 0.04,
        "coil_axis": "Z",
    },
    "HANK": {
        "coil_radius": 0.22,
        "coil_radius_end": 0.26,
        "coil_turns": 5.0,
        "coil_pitch": 0.02,
        "coil_controls_per_turn": 8,
        "coil_randomness": 0.10,
        "coil_axis": "Z",
    },
    "DRUM": {
        "coil_radius": 0.40,
        "coil_radius_end": 0.40,
        "coil_turns": 9.0,
        "coil_pitch": 0.035,
        "coil_controls_per_turn": 10,
        "coil_randomness": 0.015,
        "coil_axis": "Y",
    },
    "HEAP": {
        "coil_radius": 0.30,
        "coil_radius_end": 0.62,
        "coil_turns": 4.5,
        "coil_pitch": 0.02,
        "coil_controls_per_turn": 7,
        "coil_randomness": 0.30,
        "coil_axis": "Z",
    },
}

_suspend_coil_preset = False


def _apply_coil_preset(settings, context) -> None:
    global _suspend_coil_preset
    if _suspend_coil_preset:
        return
    values = _COIL_PRESETS.get(settings.coil_preset)
    if values is None:  # "CUSTOM" keeps whatever is set
        return

    _suspend_coil_preset = True
    try:
        for name, value in values.items():
            setattr(settings, name, value)
    finally:
        _suspend_coil_preset = False


def _coil_value_edited(settings, context) -> None:
    """Hand-editing any coil setting means the shape is no longer a named preset."""
    global _suspend_coil_preset
    if not _suspend_coil_preset and settings.coil_preset != "CUSTOM":
        _suspend_coil_preset = True
        try:
            settings.coil_preset = "CUSTOM"
        finally:
            _suspend_coil_preset = False


# Ready-made looks for cables run between objects, covering the single-cable and bundle
# modes together since a look is as much "how many wires and how far apart" as it is sag.
# Sag is carried as a fraction of the span (see utils.sag_amount): a fixed distance only
# looks right at one span length, and these are meant to hold up across a 4m alley and a
# 30m street alike.
#
# Middle Controls is kept odd throughout, so one control lands on the middle of the span
# where the sin() sag envelope peaks and the cable actually reaches the depth asked for. An
# even count straddles the middle and comes up about 5% short.
_CABLE_PRESETS = {
    "POWER_LINE": {
        "slack": 0.0,
        "slack_relative": -0.08,
        "middle_controls": 3,
        "thickness": 0.02,
        "bevel_resolution": 3,
        "bundle_count": 4,
        "bundle_spread": 0.45,
        "bundle_variation": 0.08,
    },
    "STREET_WIRES": {
        "slack": 0.0,
        "slack_relative": -0.14,
        "middle_controls": 5,
        "thickness": 0.01,
        "bevel_resolution": 2,
        "bundle_count": 7,
        "bundle_spread": 0.22,
        "bundle_variation": 0.55,
    },
    "SAGGING_DROP": {
        "slack": 0.0,
        "slack_relative": -0.28,
        "middle_controls": 5,
        "thickness": 0.012,
        "bevel_resolution": 3,
        "bundle_count": 3,
        "bundle_spread": 0.06,
        "bundle_variation": 0.45,
    },
    "CABLE_LOOM": {
        "slack": 0.0,
        "slack_relative": -0.04,
        "middle_controls": 3,
        "thickness": 0.006,
        "bevel_resolution": 3,
        "bundle_count": 6,
        "bundle_spread": 0.07,
        "bundle_variation": 0.35,
    },
    "TAUT_RUN": {
        "slack": 0.0,
        "slack_relative": -0.008,
        "middle_controls": 1,
        "thickness": 0.015,
        "bevel_resolution": 3,
        "bundle_count": 3,
        "bundle_spread": 0.03,
        "bundle_variation": 0.05,
    },
}

_suspend_cable_preset = False


def _apply_cable_preset(settings, context) -> None:
    global _suspend_cable_preset
    if _suspend_cable_preset:
        return
    values = _CABLE_PRESETS.get(settings.cable_preset)
    if values is None:  # "CUSTOM" keeps whatever is set
        return

    _suspend_cable_preset = True
    try:
        for name, value in values.items():
            setattr(settings, name, value)
    finally:
        _suspend_cable_preset = False


def _cable_value_edited(settings, context) -> None:
    """Hand-editing any of a preset's settings means the look is no longer that preset."""
    global _suspend_cable_preset
    if not _suspend_cable_preset and settings.cable_preset != "CUSTOM":
        _suspend_cable_preset = True
        try:
            settings.cable_preset = "CUSTOM"
        finally:
            _suspend_cable_preset = False


class PCG_Settings(bpy.types.PropertyGroup):
    cable_name: StringProperty(
        name="Cable Name",
        default="Cable",
        description="Name for the generated cable setup",
    )

    cable_preset: EnumProperty(
        name="Cable Preset",
        items=(
            (
                "POWER_LINE",
                "Power Line",
                "Overhead conductors strung between poles: heavy, evenly spread, with the "
                "shallow even droop of a tensioned line",
            ),
            (
                "STREET_WIRES",
                "Street Wires",
                "The untidy tangle of thin wires strung across a street or alley: many "
                "cables, deeper sag, and no two alike",
            ),
            (
                "SAGGING_DROP",
                "Sagging Drop",
                "A few slack cables hanging in a deep loop, as if left with far more length "
                "than the gap needs",
            ),
            (
                "CABLE_LOOM",
                "Cable Loom",
                "A tied harness of thin cables running close together with only slight sag",
            ),
            (
                "TAUT_RUN",
                "Taut Run",
                "A pulled-tight run with almost no droop, for guy wires and tensioned cable",
            ),
            ("CUSTOM", "Custom", "Settings edited by hand"),
        ),
        default="CUSTOM",
        description=(
            "Ready-made looks for cables run between objects. Sets sag, control count, "
            "thickness and the bundle settings together - editing any of them switches to "
            "Custom"
        ),
        update=_apply_cable_preset,
    )

    thickness: FloatProperty(
        name="Thickness",
        default=0.008,
        min=0.0,
        soft_max=0.2,
        description="Curve bevel depth",
        subtype="DISTANCE",
        unit="LENGTH",
        update=_cable_value_edited,
    )

    bevel_resolution: IntProperty(
        name="Bevel Resolution",
        default=3,
        min=0,
        max=12,
        description="Curve bevel resolution",
        update=_cable_value_edited,
    )

    middle_controls: IntProperty(
        name="Middle Controls",
        default=1,
        min=0,
        max=20,
        description="Number of middle control empties between start and end",
        update=_cable_value_edited,
    )

    chain_order: EnumProperty(
        name="Chain Order",
        items=(
            ("NEAREST", "Nearest", "Order selected objects as a nearest-neighbor chain starting from the active object"),
            ("SELECTION", "Selection", "Use Blender's selected object order (may vary)"),
            ("NAME", "Name", "Order selected objects by name"),
        ),
        default="NEAREST",
        description="How to order multiple selected objects when creating a multi-point cable",
    )

    parent_chain_controls: BoolProperty(
        name="Parent Chain Controls",
        default=False,
        description="Parent each generated control empty to its corresponding selected object",
    )

    slack: FloatProperty(
        name="Slack",
        default=0.0,
        soft_min=-2.0,
        soft_max=2.0,
        description="Offsets the middle controls along an up-ish direction (use negative for sag)",
        subtype="DISTANCE",
        unit="LENGTH",
        update=_cable_value_edited,
    )

    slack_relative: FloatProperty(
        name="Span Sag",
        default=0.0,
        soft_min=-0.6,
        soft_max=0.6,
        description=(
            "Extra sag as a fraction of the distance the cable spans, added to Slack. "
            "Negative sags downward. Being relative, one value keeps the same look on a "
            "short run and a long one, which is what the cable presets use"
        ),
        update=_cable_value_edited,
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

    free_length: FloatProperty(
        name="Free Length",
        default=2.0,
        min=0.0,
        soft_max=20.0,
        description="Initial length of a free cable created at the 3D cursor",
        subtype="DISTANCE",
        unit="LENGTH",
    )

    free_controls: IntProperty(
        name="Free Controls",
        default=6,
        min=2,
        max=64,
        description="Total number of control empties for a free cable (including start/end)",
    )

    coil_preset: EnumProperty(
        name="Coil Preset",
        items=(
            (
                "GROUND",
                "Ground Coil",
                "Cable coiled and dropped on the ground: nested rings spiralling outward, "
                "barely stacked",
            ),
            (
                "HANK",
                "Hank",
                "A tied-off hank of cable as carried or hung on a hook: tight, slightly messy",
            ),
            (
                "DRUM",
                "Cable Drum",
                "Neatly wound on a spool or reel, standing on its side",
            ),
            (
                "HEAP",
                "Loose Heap",
                "Cable dumped in an untidy pile, wide and irregular",
            ),
            ("CUSTOM", "Custom", "Settings edited by hand"),
        ),
        default="GROUND",
        description=(
            "Ready-made coil shapes. Pick one, place the 3D cursor and create - editing any "
            "coil setting switches to Custom"
        ),
        update=_apply_coil_preset,
    )

    coil_radius: FloatProperty(
        name="Inner Radius",
        default=0.28,
        min=0.001,
        soft_max=5.0,
        description="Radius where the coil starts",
        subtype="DISTANCE",
        unit="LENGTH",
        update=_coil_value_edited,
    )

    coil_radius_end: FloatProperty(
        name="Outer Radius",
        default=0.46,
        min=0.001,
        soft_max=5.0,
        description=(
            "Radius where the coil ends. Larger than the inner radius gives nested rings "
            "spiralling outward, which is how cable actually coils on the ground; equal "
            "values give a uniform drum"
        ),
        subtype="DISTANCE",
        unit="LENGTH",
        update=_coil_value_edited,
    )

    coil_turns: FloatProperty(
        name="Turns",
        default=3.5,
        min=0.25,
        soft_max=40.0,
        description="How many times the cable wraps around",
        update=_coil_value_edited,
    )

    coil_pitch: FloatProperty(
        name="Pitch",
        default=0.012,
        soft_min=-1.0,
        soft_max=2.0,
        description=(
            "Rise per turn. Small values give a coil stacked almost flat, larger values a "
            "stretched spring"
        ),
        subtype="DISTANCE",
        unit="LENGTH",
        update=_coil_value_edited,
    )

    coil_controls_per_turn: IntProperty(
        name="Controls Per Turn",
        default=8,
        min=3,
        max=24,
        description="Control empties generated per turn. Higher gives a rounder coil",
        update=_coil_value_edited,
    )

    coil_randomness: FloatProperty(
        name="Randomness",
        default=0.04,
        min=0.0,
        soft_max=1.0,
        description=(
            "Jitters the coil by this fraction of its radius, so it reads as hand-wound "
            "rather than machine-perfect"
        ),
        update=_coil_value_edited,
    )

    coil_axis: EnumProperty(
        name="Coil Axis",
        items=(
            ("Z", "Z (lying flat)", "Coil stacks upward, as if dropped on the ground"),
            ("Y", "Y", "Coil wound around the Y axis, as on a wall-mounted reel"),
            ("X", "X", "Coil wound around the X axis"),
        ),
        default="Z",
        description="Axis the cable is wound around",
        update=_coil_value_edited,
    )

    coil_seed: IntProperty(
        name="Seed",
        default=0,
        min=0,
        description="Change for a different random variation of the same coil",
    )

    bundle_count: IntProperty(
        name="Cables",
        default=4,
        min=2,
        max=32,
        description="How many cables to generate in the bundle",
        update=_cable_value_edited,
    )

    bundle_spread: FloatProperty(
        name="Spread",
        default=0.06,
        min=0.0,
        soft_max=1.0,
        description=(
            "How far the cables separate between their tied ends. Ends stay together, so the "
            "bundle reads as tied"
        ),
        subtype="DISTANCE",
        unit="LENGTH",
        update=_cable_value_edited,
    )

    bundle_variation: FloatProperty(
        name="Variation",
        default=0.35,
        min=0.0,
        max=1.0,
        description="Randomises each cable's spread and sag so they do not look cloned",
        update=_cable_value_edited,
    )

    bundle_seed: IntProperty(
        name="Seed",
        default=0,
        min=0,
        description="Change for a different random arrangement of the same bundle",
    )

    sync_selected_cables: BoolProperty(
        name="Edit All Selected Cables",
        default=True,
        description=(
            "Apply every dynamics setting change to all selected cables at once. Turn it off "
            "to tune one cable of a bundle on its own"
        ),
    )

    show_legacy: BoolProperty(
        name="Show Legacy Tools",
        default=False,
    )

    legacy_out_prefix: StringProperty(name="OUT Prefix", default="OUT_")
    legacy_mid_prefix: StringProperty(name="MID Prefix", default="MID_")
    legacy_in_prefix: StringProperty(name="IN Prefix", default="IN_")


def _update_dynamics_settings(self, context: bpy.types.Context) -> None:
    obj = self.id_data
    if dynamics.is_dynamics_enabled(obj):
        dynamics.sync_dynamics_settings(obj, self)


# Guards the mirror below against recursing: writing the value onto another cable fires that
# cable's own update callback, which would otherwise mirror it straight back.
_mirroring = False


def _mirror_to_selected_cables(settings, context: bpy.types.Context, name: str) -> None:
    """Apply one edited setting to every other selected cable.

    Dynamics settings live on the cable object, so a slider only ever writes to the active
    one. A Tied Bundle is several cables that are meant to behave alike, so without this
    every setting would have to be dialled in seven times.
    """
    global _mirroring
    # _suspend_preset_sync means a preset is mid-application: its individual writes are
    # skipped here and the preset itself is mirrored once, at the end.
    if _mirroring or _suspend_preset_sync:
        return

    scene = getattr(context, "scene", None)
    if scene is None or not scene.pcg_settings.sync_selected_cables:
        return

    source = settings.id_data
    if not dynamics.is_dynamics_enabled(source):
        return

    value = getattr(settings, name)
    _mirroring = True
    try:
        for cable in dynamics.cables_for_selection(context):
            if cable == source or not dynamics.is_dynamics_enabled(cable):
                continue
            # Writing through the property fires the target's own update callback, which
            # re-syncs its modifier and flips its preset label exactly as the source's did.
            setattr(cable.pcg_dynamics, name, value)
    finally:
        _mirroring = False


def _mirrored(name: str, handler):
    """Build an update callback for `name` that also mirrors the edit to selected cables.

    Blender does not tell an update callback which property fired it, so the name is bound
    here rather than discovered at call time.
    """

    def update(self, context: bpy.types.Context) -> None:
        handler(self, context)
        _mirror_to_selected_cables(self, context, name)

    return update


def _mirror_profile_to_curve(settings) -> None:
    # Mirror onto the curve's own bevel so the cable keeps the same thickness if dynamics
    # is later removed, and so both paths stay driven by this one setting.
    obj = settings.id_data
    if obj.type == "CURVE":
        obj.data.bevel_depth = settings.thickness
        obj.data.bevel_resolution = settings.profile_resolution


# Values a preset writes. Cables of different kinds differ mainly in thickness, how quickly
# they settle, how readily they kink, and how much momentum they carry when something drags
# them. Note that mass and bend do not change the shape of a *settled* hanging cable - that
# is fixed by its length and span - but they do change how it responds to being pushed.
_PRESETS = {
    "FLOPPY": {
        "thickness": 0.006,
        "mass": 0.3,
        "stiffness": 0.9,
        "bend": 0.05,
        "damping": 0.5,
        "friction": 0.4,
        "segment_divisions": 12,
    },
    "HEAVY": {
        "thickness": 0.04,
        "mass": 8.0,
        "stiffness": 0.95,
        "bend": 0.6,
        "damping": 2.5,
        "friction": 0.6,
        "segment_divisions": 10,
    },
    "FRAYED": {
        "thickness": 0.015,
        "mass": 1.0,
        "stiffness": 0.7,
        "bend": 0.0,
        "damping": 0.8,
        "friction": 0.8,
        "segment_divisions": 24,
    },
}

# Guards the preset <-> individual-setting round trip: applying a preset writes the
# individual settings, and editing one of those flips the preset back to Custom.
_suspend_preset_sync = False


def _apply_preset(self, context: bpy.types.Context) -> None:
    global _suspend_preset_sync
    if _suspend_preset_sync:
        return
    values = _PRESETS.get(self.preset)
    if values is None:  # "CUSTOM" keeps whatever is currently set
        return

    _suspend_preset_sync = True
    try:
        for name, value in values.items():
            setattr(self, name, value)
    finally:
        _suspend_preset_sync = False

    _mirror_profile_to_curve(self)
    _update_dynamics_settings(self, context)


def _update_preset_value(self, context: bpy.types.Context) -> None:
    """Update handler for settings a preset controls; hand-editing one means 'Custom'."""
    global _suspend_preset_sync
    if not _suspend_preset_sync and self.preset != "CUSTOM":
        _suspend_preset_sync = True
        try:
            self.preset = "CUSTOM"
        finally:
            _suspend_preset_sync = False

    _mirror_profile_to_curve(self)
    _update_dynamics_settings(self, context)


class PCG_DynamicsSettings(bpy.types.PropertyGroup):
    """Per-cable dynamics settings, active on a CABLE_* curve object once Dynamics is enabled."""

    # Set by the Enable/Disable Self Collision operators rather than edited directly:
    # switching it builds or removes a cloth proxy object, which is not safe to do from a
    # property update handler.
    use_self_collision: BoolProperty(
        name="Self Collision",
        default=False,
        description="Whether this cable is routed through the heavier legacy-cloth solver "
        "so it can collide with itself",
    )

    selfcol_object: PointerProperty(
        name="Cloth Proxy",
        type=bpy.types.Object,
        description="Internal ribbon mesh simulated by legacy Cloth when self collision is on",
    )

    self_collision_distance: FloatProperty(
        name="Self Distance",
        default=0.05,
        min=0.001,
        soft_max=0.5,
        description="How close the cable may come to itself before pushing apart. Raise it if "
        "the cable passes through itself, lower it for tighter coils",
        subtype="DISTANCE",
        unit="LENGTH",
        update=_mirrored("self_collision_distance", _update_dynamics_settings),
    )

    alembic_directory: StringProperty(
        name="Export Folder",
        default="//",
        description=(
            "Folder for Alembic (.abc) exports. Defaults to '//', which means the folder "
            "holding this .blend. Unsaved files fall back to a temporary folder"
        ),
        subtype="DIR_PATH",
    )

    # Held here rather than read back from the modifier, because the background tier's node
    # group has no Pin Anchors socket - reading it from there loses the reference as soon as
    # the tier is switched.
    anchor_object: PointerProperty(
        name="Pin Anchors",
        type=bpy.types.Object,
        description="Internal helper mesh whose vertices follow this cable's control empties",
    )

    tier: EnumProperty(
        name="Tier",
        items=(
            (
                "HERO",
                "Hero",
                "Full cloth simulation with pinning and collision. Use for cables the shot "
                "actually features",
            ),
            (
                "BACKGROUND",
                "Background",
                "Cheap procedural sway with no solver and no collision. Use for the many cables "
                "that only need to look alive",
            ),
        ),
        default="HERO",
        description="How much simulation this cable gets",
        update=_mirrored("tier", _update_dynamics_settings),
    )

    sway_amount: FloatProperty(
        name="Sway Amount",
        default=0.05,
        min=0.0,
        soft_max=1.0,
        description="How far a background cable drifts from its resting shape",
        subtype="DISTANCE",
        unit="LENGTH",
        update=_mirrored("sway_amount", _update_dynamics_settings),
    )

    sway_speed: FloatProperty(
        name="Sway Speed",
        default=0.3,
        min=0.0,
        soft_max=5.0,
        description="How quickly a background cable's sway animates",
        update=_mirrored("sway_speed", _update_dynamics_settings),
    )

    sway_scale: FloatProperty(
        name="Sway Scale",
        default=0.5,
        min=0.0,
        soft_max=5.0,
        description="Size of the sway pattern along the cable. Lower values bend it as a whole, "
        "higher values ripple it",
        update=_mirrored("sway_scale", _update_dynamics_settings),
    )

    sway_resample: IntProperty(
        name="Sway Resolution",
        default=24,
        min=2,
        soft_max=100,
        description="Points used to draw a background cable's sway",
        update=_mirrored("sway_resample", _update_dynamics_settings),
    )

    preset: EnumProperty(
        name="Preset",
        items=(
            ("FLOPPY", "Floppy Wire", "Thin, light, easily kinked wire"),
            ("HEAVY", "Heavy Cable", "Thick cable with weight and momentum that settles slowly"),
            (
                "FRAYED",
                "Frayed Tangle",
                "Messy, high-resolution cable that kinks and grips readily. Pair with Self "
                "Collision for tangling once that is available",
            ),
            ("CUSTOM", "Custom", "Settings edited by hand"),
        ),
        default="CUSTOM",
        description="Starting point for a kind of cable. Editing any of its settings switches to Custom",
        update=_mirrored("preset", _apply_preset),
    )

    thickness: FloatProperty(
        name="Thickness",
        default=0.008,
        min=0.0,
        soft_max=0.2,
        description="Visual radius of the cable tube",
        subtype="DISTANCE",
        unit="LENGTH",
        update=_mirrored("thickness", _update_preset_value),
    )

    profile_resolution: IntProperty(
        name="Profile Resolution",
        default=3,
        min=0,
        max=12,
        description="Roundness of the cable's cross-section",
        update=_mirrored("profile_resolution", _update_preset_value),
    )

    mass: FloatProperty(
        name="Mass",
        default=1.0,
        min=0.001,
        soft_max=20.0,
        description="Simulated mass of the cable; higher values add weight and momentum",
        update=_mirrored("mass", _update_preset_value),
    )

    stiffness: FloatProperty(
        name="Stiffness",
        default=0.8,
        min=0.0,
        max=1.0,
        description="Resistance to stretching along the cable's length (0 = very stretchy, 1 = rigid)",
        update=_mirrored("stiffness", _update_preset_value),
    )

    bend: FloatProperty(
        name="Bend Resistance",
        default=0.5,
        min=0.0,
        max=1.0,
        description="Resistance to bending/kinking (0 = very floppy, 1 = stiff)",
        update=_mirrored("bend", _update_preset_value),
    )

    damping: FloatProperty(
        name="Damping",
        default=1.0,
        min=0.0,
        soft_max=10.0,
        description="Linear damping applied to the simulation; higher values settle faster with less swing",
        update=_mirrored("damping", _update_preset_value),
    )

    friction: FloatProperty(
        name="Friction",
        default=0.5,
        min=0.0,
        max=1.0,
        description="Surface friction used against colliders",
        update=_mirrored("friction", _update_preset_value),
    )

    collision_radius: FloatProperty(
        name="Collision Radius",
        default=0.02,
        min=0.001,
        soft_max=0.5,
        description="Effective thickness used for collision purposes (independent of the visual bevel thickness)",
        subtype="DISTANCE",
        unit="LENGTH",
        update=_mirrored("collision_radius", _update_dynamics_settings),
    )

    substeps: IntProperty(
        name="Substeps",
        default=5,
        min=1,
        soft_max=20,
        description="Simulation substeps per frame; higher is more stable but slower. Raise with care",
        update=_mirrored("substeps", _update_dynamics_settings),
    )

    constraint_steps: IntProperty(
        name="Constraint Steps",
        default=15,
        min=1,
        soft_max=50,
        description="Constraint solver iterations per substep; higher is more stable but slower. Raise with care",
        update=_mirrored("constraint_steps", _update_dynamics_settings),
    )

    pin_mode: EnumProperty(
        name="Pin Controls",
        items=(
            (
                "ALL",
                "All Controls",
                "Pin the cable at every CTRL_* control, so the whole cable holds the pose you set",
            ),
            (
                "ENDS",
                "Ends Only",
                "Pin only the first and last control. Middle controls still shape the cable's rest "
                "path, but the span between them is free to drape and collide",
            ),
            ("NONE", "None", "Pin nothing, letting the whole cable fall freely"),
        ),
        default="ALL",
        description="Which control empties hold the cable in place during simulation",
        update=_mirrored("pin_mode", _update_dynamics_settings),
    )

    collision_collection: PointerProperty(
        name="Collision Collection",
        type=bpy.types.Collection,
        description=(
            "Collection of collider objects the cable can hit. Use 'Add Selected As Colliders' "
            "to set characters and props up for this"
        ),
        update=_mirrored("collision_collection", _update_dynamics_settings),
    )

    segment_divisions: IntProperty(
        name="Divisions Per Segment",
        default=8,
        min=1,
        soft_max=32,
        description=(
            "Simulated points generated between each pair of CTRL_* controls. "
            "Higher gives smoother sag at a higher cost"
        ),
        update=_mirrored("segment_divisions", _update_preset_value),
    )
