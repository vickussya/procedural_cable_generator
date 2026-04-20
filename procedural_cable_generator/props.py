import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty


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

