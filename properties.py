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
        update=_apply_preset,
    )

    thickness: FloatProperty(
        name="Thickness",
        default=0.008,
        min=0.0,
        soft_max=0.2,
        description="Visual radius of the cable tube",
        subtype="DISTANCE",
        unit="LENGTH",
        update=_update_preset_value,
    )

    profile_resolution: IntProperty(
        name="Profile Resolution",
        default=3,
        min=0,
        max=12,
        description="Roundness of the cable's cross-section",
        update=_update_preset_value,
    )

    mass: FloatProperty(
        name="Mass",
        default=1.0,
        min=0.001,
        soft_max=20.0,
        description="Simulated mass of the cable; higher values add weight and momentum",
        update=_update_preset_value,
    )

    stiffness: FloatProperty(
        name="Stiffness",
        default=0.8,
        min=0.0,
        max=1.0,
        description="Resistance to stretching along the cable's length (0 = very stretchy, 1 = rigid)",
        update=_update_preset_value,
    )

    bend: FloatProperty(
        name="Bend Resistance",
        default=0.5,
        min=0.0,
        max=1.0,
        description="Resistance to bending/kinking (0 = very floppy, 1 = stiff)",
        update=_update_preset_value,
    )

    damping: FloatProperty(
        name="Damping",
        default=1.0,
        min=0.0,
        soft_max=10.0,
        description="Linear damping applied to the simulation; higher values settle faster with less swing",
        update=_update_preset_value,
    )

    friction: FloatProperty(
        name="Friction",
        default=0.5,
        min=0.0,
        max=1.0,
        description="Surface friction used against colliders",
        update=_update_preset_value,
    )

    collision_radius: FloatProperty(
        name="Collision Radius",
        default=0.02,
        min=0.001,
        soft_max=0.5,
        description="Effective thickness used for collision purposes (independent of the visual bevel thickness)",
        subtype="DISTANCE",
        unit="LENGTH",
        update=_update_dynamics_settings,
    )

    substeps: IntProperty(
        name="Substeps",
        default=5,
        min=1,
        soft_max=20,
        description="Simulation substeps per frame; higher is more stable but slower. Raise with care",
        update=_update_dynamics_settings,
    )

    constraint_steps: IntProperty(
        name="Constraint Steps",
        default=15,
        min=1,
        soft_max=50,
        description="Constraint solver iterations per substep; higher is more stable but slower. Raise with care",
        update=_update_dynamics_settings,
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
        update=_update_dynamics_settings,
    )

    collision_collection: PointerProperty(
        name="Collision Collection",
        type=bpy.types.Collection,
        description=(
            "Collection of collider objects the cable can hit. Use 'Add Selected As Colliders' "
            "to set characters and props up for this"
        ),
        update=_update_dynamics_settings,
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
        update=_update_preset_value,
    )
