import contextlib
import math
import os
import random

import bpy

from . import dynamics
from .utils import (
    bundle_offset,
    create_cable_curve,
    ensure_root_collection,
    helix_positions,
    is_cable_curve_object,
    make_empty,
    new_child_collection,
    offset_dir_for_slack,
    ordered_selected_pair,
    parent_keep_world,
    perpendicular_basis,
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


class PCG_OT_create_coiled_cable(bpy.types.Operator):
    bl_idname = "pcg.create_coiled_cable"
    bl_label = "Create Coiled Cable (Cursor)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.mode == "OBJECT"

    def execute(self, context: bpy.types.Context):
        settings = context.scene.pcg_settings
        count = max(3, int(round(settings.coil_turns * settings.coil_controls_per_turn)) + 1)

        positions = helix_positions(
            origin=context.scene.cursor.location.copy(),
            radius=settings.coil_radius,
            radius_end=settings.coil_radius_end,
            turns=settings.coil_turns,
            pitch=settings.coil_pitch,
            count=count,
            axis=settings.coil_axis,
            randomness=settings.coil_randomness,
            seed=settings.coil_seed,
        )

        root = ensure_root_collection(context.scene)
        cable_coll = new_child_collection(root, f"Cable_{settings.cable_name}")
        controls = _create_controls_for_positions(
            cable_coll=cable_coll,
            cable_base_name=settings.cable_name,
            positions=positions,
            empty_size=settings.empty_size,
            parent_objects=None,
        )

        existing_names = {o.name for o in bpy.data.objects} | {c.name for c in bpy.data.curves}
        curve_obj = create_cable_curve(
            collection=cable_coll,
            cable_name=unique_name(f"CABLE_{settings.cable_name}", existing_names),
            controls=controls,
            thickness=settings.thickness,
            bevel_resolution=settings.bevel_resolution,
        )

        context.view_layer.objects.active = curve_obj
        curve_obj.select_set(True)
        self.report(
            {"INFO"},
            f"Created coiled cable '{curve_obj.name}': "
            f"{settings.coil_turns:g} turns, {len(controls)} controls",
        )
        return {"FINISHED"}


class PCG_OT_create_cable_bundle(bpy.types.Operator):
    bl_idname = "pcg.create_cable_bundle"
    bl_label = "Create Tied Bundle From 2 Objects"
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

        start_pos = start_obj.matrix_world.translation.copy()
        end_pos = end_obj.matrix_world.translation.copy()
        basis_a, basis_b = perpendicular_basis(start_pos, end_pos)
        slack_dir = offset_dir_for_slack(start_pos, end_pos)
        middle_controls = max(1, settings.middle_controls)

        root = ensure_root_collection(context.scene)
        generator = random.Random(settings.bundle_seed)
        created = []

        for cable_index in range(settings.bundle_count):
            offset = bundle_offset(
                index=cable_index,
                count=settings.bundle_count,
                spread=settings.bundle_spread,
                basis_a=basis_a,
                basis_b=basis_b,
                variation=settings.bundle_variation,
                seed=settings.bundle_seed,
            )
            # Vary each cable's sag a little so the bundle does not look cloned.
            sag = settings.slack * (1.0 + generator.uniform(-settings.bundle_variation, settings.bundle_variation))

            base_name = f"{settings.cable_name}_{cable_index + 1:02d}"
            cable_coll = new_child_collection(root, f"Cable_{base_name}")

            positions = [start_pos.copy()]
            for i in range(middle_controls):
                t = (i + 1) / (middle_controls + 1)
                envelope = math.sin(math.pi * t)
                # The offset tapers to zero at both ends, which is what makes the bundle
                # read as tied there and loose in between.
                point = start_pos.lerp(end_pos, t) + offset * envelope + slack_dir * (sag * envelope)
                positions.append(point)
            positions.append(end_pos.copy())

            parent_objs = None
            if settings.parent_end_controls:
                parent_objs = [start_obj] + [None] * middle_controls + [end_obj]

            controls = _create_controls_for_positions(
                cable_coll=cable_coll,
                cable_base_name=base_name,
                positions=positions,
                empty_size=settings.empty_size,
                parent_objects=parent_objs,
            )

            existing_names = {o.name for o in bpy.data.objects} | {c.name for c in bpy.data.curves}
            curve_obj = create_cable_curve(
                collection=cable_coll,
                cable_name=unique_name(f"CABLE_{base_name}", existing_names),
                controls=controls,
                thickness=settings.thickness,
                bevel_resolution=settings.bevel_resolution,
            )
            created.append(curve_obj)

        if created:
            context.view_layer.objects.active = created[-1]
            for obj in created:
                obj.select_set(True)

        self.report({"INFO"}, f"Created a tied bundle of {len(created)} cables")
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


def selected_cables(context: bpy.types.Context) -> list[bpy.types.Object]:
    """Cables the dynamics tools act on: the whole selection, plus the active object's cable.

    A Tied Bundle or a set of coils is several cable curves, and they are all left selected
    after generation, so acting on the active object alone would silently skip the rest.
    """
    objects = list(context.selected_objects or [])
    active = context.active_object
    if active is not None and active not in objects:
        objects.append(active)
    return dynamics.resolve_cables_for_objects(objects)


def _describe(cables: list[bpy.types.Object]) -> str:
    """Name a single cable, or count them, for operator reports."""
    if len(cables) == 1:
        return f"'{cables[0].name}'"
    return f"{len(cables)} cables"


@contextlib.contextmanager
def _only_selected(context: bpy.types.Context, objects: list[bpy.types.Object]):
    """Narrow the selection to `objects`, for Blender operators that act on selected=True."""
    previous = list(context.selected_objects or [])
    previous_active = context.active_object

    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    if objects:
        context.view_layer.objects.active = objects[0]

    try:
        yield
    finally:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in previous:
            obj.select_set(True)
        context.view_layer.objects.active = previous_active


class PCG_OT_make_cable_dynamic(bpy.types.Operator):
    bl_idname = "pcg.make_cable_dynamic"
    bl_label = "Make Dynamic"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        if context.mode != "OBJECT":
            return False
        return any(not dynamics.is_dynamics_enabled(c) for c in selected_cables(context))

    def execute(self, context: bpy.types.Context):
        cables = [c for c in selected_cables(context) if not dynamics.is_dynamics_enabled(c)]
        if not cables:
            self.report({"ERROR"}, "No cable curve without dynamics found in the selection")
            return {"CANCELLED"}

        enabled: list[bpy.types.Object] = []
        failures: list[str] = []
        for cable in cables:
            try:
                dynamics.enable_dynamics(cable, cable.pcg_dynamics)
            except dynamics.DynamicsError as exc:
                failures.append(f"{cable.name}: {exc}")
            else:
                enabled.append(cable)

        if not enabled:
            self.report({"ERROR"}, failures[0])
            return {"CANCELLED"}

        if failures:
            self.report(
                {"WARNING"},
                f"Dynamics enabled on {_describe(enabled)}; "
                f"{len(failures)} skipped - {failures[0]}",
            )
        else:
            self.report({"INFO"}, f"Dynamics enabled on {_describe(enabled)}")
        return {"FINISHED"}


class PCG_OT_remove_cable_dynamics(bpy.types.Operator):
    bl_idname = "pcg.remove_cable_dynamics"
    bl_label = "Remove Dynamics"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.mode == "OBJECT" and any(
            dynamics.is_dynamics_enabled(c) for c in selected_cables(context)
        )

    def execute(self, context: bpy.types.Context):
        cables = [c for c in selected_cables(context) if dynamics.is_dynamics_enabled(c)]
        if not cables:
            self.report({"ERROR"}, "No cable with dynamics found in the selection")
            return {"CANCELLED"}

        for cable in cables:
            dynamics.disable_dynamics(cable)
        self.report({"INFO"}, f"Dynamics removed from {_describe(cables)}")
        return {"FINISHED"}


class PCG_OT_copy_dynamics_settings(bpy.types.Operator):
    bl_idname = "pcg.copy_dynamics_settings"
    bl_label = "Copy Settings To Selected"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        if context.mode != "OBJECT":
            return False
        source = dynamics.resolve_cable_for_object(context.active_object)
        if not dynamics.is_dynamics_enabled(source):
            return False
        return any(
            c is not source and dynamics.is_dynamics_enabled(c) for c in selected_cables(context)
        )

    def execute(self, context: bpy.types.Context):
        source = dynamics.resolve_cable_for_object(context.active_object)
        if not dynamics.is_dynamics_enabled(source):
            self.report({"ERROR"}, "The active object is not a cable with dynamics enabled")
            return {"CANCELLED"}

        targets = [
            c
            for c in selected_cables(context)
            if c is not source and dynamics.is_dynamics_enabled(c)
        ]
        if not targets:
            self.report({"ERROR"}, "Select the other cables to copy these settings onto")
            return {"CANCELLED"}

        for target in targets:
            dynamics.copy_dynamics_settings(source.pcg_dynamics, target.pcg_dynamics)

        self.report({"INFO"}, f"Copied '{source.name}' dynamics settings to {_describe(targets)}")
        return {"FINISHED"}


class _CableDynamicsOperator(bpy.types.Operator):
    """Shared polling for operators acting on the selected cables' dynamics setups."""

    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.mode == "OBJECT" and any(
            dynamics.is_dynamics_enabled(c) for c in selected_cables(context)
        )

    def _cables(self, context: bpy.types.Context) -> list[bpy.types.Object]:
        cables = [c for c in selected_cables(context) if dynamics.is_dynamics_enabled(c)]
        if not cables:
            self.report({"ERROR"}, "No cable with dynamics found in the selection")
        return cables


class PCG_OT_enable_self_collision(_CableDynamicsOperator):
    bl_idname = "pcg.enable_self_collision"
    bl_label = "Enable Self Collision"

    def execute(self, context: bpy.types.Context):
        cables = self._cables(context)
        if not cables:
            return {"CANCELLED"}

        enabled: list[bpy.types.Object] = []
        failures: list[str] = []
        for cable in cables:
            # Already-on cables are skipped rather than failed, so one cable being set up
            # does not block the rest of a selection.
            if cable.pcg_dynamics.use_self_collision:
                continue
            try:
                dynamics.enable_self_collision(cable)
            except dynamics.DynamicsError as exc:
                failures.append(f"{cable.name}: {exc}")
            else:
                enabled.append(cable)

        if not enabled:
            self.report(
                {"ERROR"},
                failures[0] if failures else "Self collision is already enabled on these cables",
            )
            return {"CANCELLED"}

        message = (
            f"Self collision on {_describe(enabled)} uses the heavier legacy cloth solver; "
            "expect slower playback"
        )
        if failures:
            message += f" ({len(failures)} skipped - {failures[0]})"
        self.report({"WARNING"}, message)
        return {"FINISHED"}


class PCG_OT_disable_self_collision(_CableDynamicsOperator):
    bl_idname = "pcg.disable_self_collision"
    bl_label = "Disable Self Collision"

    def execute(self, context: bpy.types.Context):
        cables = self._cables(context)
        if not cables:
            return {"CANCELLED"}

        removed = [c for c in cables if c.pcg_dynamics.use_self_collision]
        if not removed:
            self.report({"ERROR"}, "No selected cable has self collision enabled")
            return {"CANCELLED"}

        for cable in removed:
            dynamics.disable_self_collision(cable)
        self.report({"INFO"}, f"Self collision removed from {_describe(removed)}")
        return {"FINISHED"}


class PCG_OT_bake_simulation(_CableDynamicsOperator):
    bl_idname = "pcg.bake_simulation"
    bl_label = "Bake Simulation"

    def execute(self, context: bpy.types.Context):
        cables = self._cables(context)
        if not cables:
            return {"CANCELLED"}

        simulated = [c for c in cables if c.pcg_dynamics.tier != dynamics.TIER_BACKGROUND]
        if not simulated:
            self.report({"ERROR"}, "Background cables have no simulation to bake")
            return {"CANCELLED"}

        # The operator works on the selection, so narrow it to the cables being baked.
        with _only_selected(context, simulated):
            try:
                bpy.ops.object.simulation_nodes_cache_bake(selected=True)
            except RuntimeError as exc:
                self.report({"ERROR"}, f"Bake failed: {exc}")
                return {"CANCELLED"}

        self.report({"INFO"}, f"Baked simulation cache for {_describe(simulated)}")
        return {"FINISHED"}


class PCG_OT_delete_simulation_bake(_CableDynamicsOperator):
    bl_idname = "pcg.delete_simulation_bake"
    bl_label = "Delete Bake"

    def execute(self, context: bpy.types.Context):
        cables = self._cables(context)
        if not cables:
            return {"CANCELLED"}

        with _only_selected(context, cables):
            try:
                bpy.ops.object.simulation_nodes_cache_delete(selected=True)
            except RuntimeError as exc:
                self.report({"ERROR"}, f"Could not delete bake: {exc}")
                return {"CANCELLED"}

        self.report({"INFO"}, f"Deleted simulation cache for {_describe(cables)}")
        return {"FINISHED"}


class PCG_OT_export_cable_alembic(_CableDynamicsOperator):
    bl_idname = "pcg.export_cable_alembic"
    bl_label = "Export Alembic (.abc)"

    def execute(self, context: bpy.types.Context):
        cables = self._cables(context)
        if not cables:
            return {"CANCELLED"}

        scene = context.scene
        exported: list[str] = []
        warning = None

        # One file per cable, named after it: each cable carries its own export folder, and
        # a per-cable file stays usable when only part of a bundle is re-exported.
        for cable in cables:
            directory, cable_warning = dynamics.resolve_alembic_directory(cable.pcg_dynamics)
            warning = warning or cable_warning
            try:
                os.makedirs(directory, exist_ok=True)
            except OSError as exc:
                self.report({"ERROR"}, f"Could not create export folder '{directory}': {exc}")
                return {"CANCELLED"}

            filepath = os.path.join(directory, f"{cable.name}.abc")
            with _only_selected(context, [cable]):
                try:
                    bpy.ops.wm.alembic_export(
                        filepath=filepath,
                        selected=True,
                        start=scene.frame_start,
                        end=scene.frame_end,
                        # Run synchronously so the report reflects a finished file rather
                        # than a job that is still writing.
                        as_background_job=False,
                        evaluation_mode="RENDER",
                    )
                except RuntimeError as exc:
                    self.report({"ERROR"}, f"Alembic export failed for '{cable.name}': {exc}")
                    return {"CANCELLED"}
            exported.append(filepath)

        if warning:
            self.report({"WARNING"}, warning)
        elif len(exported) == 1:
            self.report(
                {"INFO"},
                f"Exported frames {scene.frame_start}-{scene.frame_end} to {exported[0]}",
            )
        else:
            self.report(
                {"INFO"},
                f"Exported frames {scene.frame_start}-{scene.frame_end} of {len(exported)} "
                f"cables to {os.path.dirname(exported[0])}",
            )
        return {"FINISHED"}


class PCG_OT_bake_cable_to_mesh(_CableDynamicsOperator):
    bl_idname = "pcg.bake_cable_to_mesh"
    bl_label = "Convert To Baked Mesh"

    def execute(self, context: bpy.types.Context):
        cables = self._cables(context)
        if not cables:
            return {"CANCELLED"}

        scene = context.scene
        original_frame = scene.frame_current
        baked: list[bpy.types.Object] = []
        frames = 0
        try:
            for cable in cables:
                baked_obj, frames = dynamics.bake_cable_to_mesh(
                    cable, scene.frame_start, scene.frame_end
                )
                baked.append(baked_obj)
        except dynamics.DynamicsError as exc:
            # Whatever baked before the failure is kept; report which cable stopped it.
            self.report({"ERROR"}, f"{cables[len(baked)].name}: {exc}")
            return {"CANCELLED"}
        finally:
            scene.frame_set(original_frame)

        if len(baked) == 1:
            self.report(
                {"INFO"},
                f"Baked {frames} frame(s) of '{cables[0].name}' into '{baked[0].name}' "
                "(self-contained)",
            )
        else:
            self.report(
                {"INFO"},
                f"Baked {frames} frame(s) of {len(baked)} cables into self-contained meshes",
            )
        return {"FINISHED"}


def _resolve_target_bone(context: bpy.types.Context, armature: bpy.types.Object) -> str | None:
    """Find which bone of `armature` a control should follow, or None if unclear.

    Note that bone selection lives on `PoseBone.select` rather than `Bone.select`, and that
    picking a bone in the Outliner sets neither, which is why several routes are tried.
    """
    active_pose_bone = getattr(context, "active_pose_bone", None)
    if active_pose_bone is not None and active_pose_bone.id_data is armature:
        return active_pose_bone.name

    active_bone = armature.data.bones.active
    if active_bone is not None:
        return active_bone.name

    selected = [pose_bone.name for pose_bone in armature.pose.bones if pose_bone.select]
    if len(selected) == 1:
        return selected[0]
    return None


class PCG_OT_attach_control(bpy.types.Operator):
    bl_idname = "pcg.attach_control"
    bl_label = "Attach Controls To Active"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        if context.mode != "OBJECT":
            return False
        target = context.active_object
        if target is None:
            return False
        return any(
            obj is not target and obj.type == "EMPTY" for obj in (context.selected_objects or [])
        )

    def execute(self, context: bpy.types.Context):
        target = context.active_object
        controls = [
            obj for obj in context.selected_objects if obj is not target and obj.type == "EMPTY"
        ]
        if not controls:
            self.report({"ERROR"}, "Select one or more control empties, then the target last")
            return {"CANCELLED"}

        # On an armature, resolve which bone the control should follow. Attaching to the
        # armature *object* instead would look like it worked while never following the
        # rig's bone animation, so a bone that cannot be identified is an error.
        bone_name = None
        if target.type == "ARMATURE":
            bone_name = _resolve_target_bone(context, target)
            if bone_name is None:
                self.report(
                    {"ERROR"},
                    "No bone identified on the armature. Select the bone in Pose Mode "
                    "(clicking it in the Outliner is not enough), then try again",
                )
                return {"CANCELLED"}

        for ctrl in controls:
            parent_keep_world(ctrl, target, bone_name)

        where = f"bone '{bone_name}'" if bone_name else f"'{target.name}'"
        self.report({"INFO"}, f"Attached {len(controls)} control(s) to {where}")
        return {"FINISHED"}


class PCG_OT_detach_control(bpy.types.Operator):
    bl_idname = "pcg.detach_control"
    bl_label = "Detach Controls"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.mode == "OBJECT" and any(
            obj.type == "EMPTY" and obj.parent is not None
            for obj in (context.selected_objects or [])
        )

    def execute(self, context: bpy.types.Context):
        detached = 0
        for obj in context.selected_objects:
            if obj.type != "EMPTY" or obj.parent is None:
                continue
            world = obj.matrix_world.copy()
            obj.parent = None
            obj.parent_type = "OBJECT"
            obj.parent_bone = ""
            obj.matrix_world = world
            detached += 1

        if detached == 0:
            self.report({"ERROR"}, "No parented control empties selected")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Detached {detached} control(s), keeping their position")
        return {"FINISHED"}


class PCG_OT_add_selected_colliders(bpy.types.Operator):
    bl_idname = "pcg.add_selected_colliders"
    bl_label = "Add Selected As Colliders"
    bl_options = {"REGISTER", "UNDO"}

    margin: bpy.props.FloatProperty(
        name="Margin",
        default=0.01,
        min=0.0,
        soft_max=0.5,
        description="Extra standoff kept around the collider surface. Raise it if cables sink into "
        "fast-moving or thin geometry",
        subtype="DISTANCE",
        unit="LENGTH",
    )

    friction: bpy.props.FloatProperty(
        name="Friction",
        default=0.2,
        min=0.0,
        max=1.0,
        description="How much the collider surface grips cables that slide across it",
    )

    deforming: bpy.props.BoolProperty(
        name="Deforming",
        default=True,
        description="Enable for animated or armature-driven meshes whose shape changes over time",
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.mode == "OBJECT" and any(
            o.type == "MESH" for o in (context.selected_objects or [])
        )

    def execute(self, context: bpy.types.Context):
        cables = [c for c in selected_cables(context) if dynamics.is_dynamics_enabled(c)]
        # A cable's pin anchor and cloth proxy are meshes sitting in the cable's own
        # collection, so selecting a bundle picks them up too. Colliding a cable against its
        # own simulation helpers would fight the solver, so they are never made colliders.
        skip = set(cables) | dynamics.cable_helper_objects()
        meshes = [o for o in context.selected_objects if o.type == "MESH" and o not in skip]
        if not meshes:
            self.report({"ERROR"}, "Select one or more mesh objects to use as colliders")
            return {"CANCELLED"}

        try:
            collection = dynamics.ensure_collider_collection(context.scene)
            added = 0
            for obj in meshes:
                if dynamics.make_collider(
                    obj, deforming=self.deforming, friction=self.friction, margin=self.margin
                ):
                    added += 1
                if obj.name not in collection.objects:
                    collection.objects.link(obj)
        except dynamics.DynamicsError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        summary = f"{len(meshes)} object(s) in '{collection.name}' ({added} newly set up as colliders)"

        # Selecting the cables alongside the collider meshes assigns the collection to all
        # of them at once, which is how a whole bundle gets its colliders in one click.
        if cables:
            for cable in cables:
                cable.pcg_dynamics.collision_collection = collection
            self.report({"INFO"}, f"{summary}; assigned to {_describe(cables)}")
            return {"FINISHED"}

        # Setting up colliders means the collider meshes are selected, not a cable, so
        # adopt these colliders on any dynamic cable that has none chosen yet. Cables with
        # a collection already set are left alone.
        adopted = [
            obj
            for obj in bpy.data.objects
            if dynamics.is_dynamics_enabled(obj) and obj.pcg_dynamics.collision_collection is None
        ]
        for obj in adopted:
            obj.pcg_dynamics.collision_collection = collection

        if adopted:
            self.report({"INFO"}, f"{summary}; assigned to {len(adopted)} cable(s)")
        else:
            self.report(
                {"INFO"},
                f"{summary}. Set a cable's Collision Collection to '{collection.name}' to use them",
            )
        return {"FINISHED"}
