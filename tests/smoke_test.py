# SPDX-License-Identifier: GPL-3.0-or-later
#
# Procedural Cable Generator - a Blender add-on for editable, procedural cables.
# Copyright (C) 2026 Vickussya
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Headless smoke test for the Procedural Cable Generator add-on.

    blender -b --factory-startup --python tests/smoke_test.py

By default the add-on is staged from this repository into a temporary script directory, so
the user's own Blender add-ons folder is never touched. Pass `-- --use-installed` to test a
copy that is already installed (e.g. from the release ZIP) instead.

Exits with code 1 if any check fails.
"""

import os
import shutil
import sys
import tempfile
import traceback

import addon_utils
import bpy

ADDON_NAME = "procedural_cable_generator"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON_FILES = ("__init__.py", "operators.py", "properties.py", "panel.py", "utils.py", "dynamics.py", "LICENSE")

results: list[tuple[str, str, str]] = []


def record(name: str, status: str, detail: str = "") -> None:
    results.append((name, status, detail))
    print(f"[{status}] {name}{(' - ' + detail) if detail else ''}", flush=True)


def check(name: str):
    """Decorator: run a test function, recording PASS, FAIL (assertion) or ERROR (exception)."""

    def wrap(fn):
        try:
            outcome = fn()
        except AssertionError as exc:
            record(name, "FAIL", str(exc))
        except Exception:  # noqa: BLE001 - any crash is a test failure
            record(name, "FAIL", traceback.format_exc().strip().splitlines()[-1])
        else:
            if isinstance(outcome, str) and outcome.startswith("SKIP"):
                record(name, "SKIP", outcome[5:].strip())
            else:
                record(name, "PASS", outcome or "")
        return fn

    return wrap


def script_args() -> list[str]:
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def stage_addon() -> str:
    """Copy the add-on into a temp script directory and register that directory with Blender."""
    scripts_dir = tempfile.mkdtemp(prefix="pcg_smoke_")
    package_dir = os.path.join(scripts_dir, "addons", ADDON_NAME)
    os.makedirs(package_dir)
    for name in ADDON_FILES:
        shutil.copy2(os.path.join(REPO_ROOT, name), package_dir)

    entry = bpy.context.preferences.filepaths.script_directories.new()
    entry.name = "pcg_smoke"
    entry.directory = scripts_dir
    bpy.utils.refresh_script_paths()
    addon_utils.modules_refresh()
    return scripts_dir


def reset_scene() -> None:
    """Empty the scene and orphan data so each mode starts from a clean slate."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for datablocks in (bpy.data.curves, bpy.data.meshes, bpy.data.node_groups):
        for block in list(datablocks):
            datablocks.remove(block)
    bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
    bpy.context.scene.pcg_settings.cable_name = "Cable"
    # Removing objects leaves the view layer's object list stale until it is re-evaluated.
    bpy.context.view_layer.update()


def add_anchor(location) -> bpy.types.Object:
    obj = bpy.data.objects.new(f"ANCHOR_{len(bpy.data.objects)}", None)
    obj.location = location
    bpy.context.scene.collection.objects.link(obj)
    return obj


def select_only(objects, active) -> None:
    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active


def cable_curves() -> list[bpy.types.Object]:
    return [o for o in bpy.data.objects if o.type == "CURVE" and o.name.startswith("CABLE_")]


def assert_cables(expected_cables: int, expected_points: int) -> list[bpy.types.Object]:
    root = bpy.data.collections.get("Procedural Cables")
    assert root is not None, "'Procedural Cables' collection missing"
    assert root.name in bpy.context.scene.collection.children, "'Procedural Cables' not linked to scene"
    cables = cable_curves()
    assert len(cables) == expected_cables, f"expected {expected_cables} CABLE_* curve(s), found {len(cables)}"
    for cable in cables:
        points = len(cable.data.splines[0].bezier_points)
        assert points == expected_points, f"{cable.name}: expected {expected_points} points, found {points}"
        owner = cable.users_collection[0]
        assert owner.name.startswith("Cable_") and owner.name in root.children, (
            f"{cable.name} is not in a Cable_* child collection"
        )
        controls = [o for o in owner.objects if o.type == "EMPTY" and o.name.startswith("CTRL_")]
        assert len(controls) == expected_points, f"{cable.name}: expected {expected_points} CTRL_* empties"
        drivers = cable.data.animation_data.drivers if cable.data.animation_data else []
        assert len(drivers) == expected_points * 3, f"{cable.name}: expected {expected_points * 3} drivers"
    return cables


def run_op(op) -> None:
    result = op()
    assert result == {"FINISHED"}, f"operator returned {result}"


def main() -> int:
    print(f"\n=== PCG smoke test: Blender {bpy.app.version_string} ===", flush=True)
    use_installed = "--use-installed" in script_args()
    staged_dir = None
    if not use_installed:
        staged_dir = stage_addon()

    addon_module = None

    @check("Enable add-on" + (" (installed copy)" if use_installed else " (staged from repo)"))
    def _():
        nonlocal addon_module
        errors: list[str] = []
        addon_module = addon_utils.enable(ADDON_NAME, default_set=True, handle_error=lambda e: errors.append(str(e)))
        assert addon_module is not None and not errors, f"enable failed: {errors}"
        assert hasattr(bpy.types.Scene, "pcg_settings"), "Scene.pcg_settings not registered"
        assert hasattr(bpy.types.Object, "pcg_dynamics"), "Object.pcg_dynamics not registered"
        return f"loaded from {os.path.dirname(addon_module.__file__)}"

    if addon_module is None:
        return summarize()

    from importlib import import_module

    dynamics = import_module(f"{ADDON_NAME}.dynamics")
    settings = bpy.context.scene.pcg_settings

    @check("Mode: From 2 Objects")
    def _():
        reset_scene()
        start, end = add_anchor((0, 0, 0)), add_anchor((4, 0, 2))
        select_only([start, end], start)
        run_op(bpy.ops.pcg.create_cable_from_selection)
        assert_cables(1, settings.middle_controls + 2)

    @check("Mode: Chain")
    def _():
        reset_scene()
        anchors = [add_anchor((x, x % 2, 0)) for x in range(4)]
        select_only(anchors, anchors[0])
        run_op(bpy.ops.pcg.create_cable_from_object_chain)
        assert_cables(1, 4)

    @check("Mode: Free Cable")
    def _():
        reset_scene()
        select_only([], None)
        run_op(bpy.ops.pcg.create_free_cable)
        assert_cables(1, settings.free_controls)

    @check("Mode: Coil / Roll")
    def _():
        reset_scene()
        select_only([], None)
        run_op(bpy.ops.pcg.create_coiled_cable)
        expected = max(3, int(round(settings.coil_turns * settings.coil_controls_per_turn)) + 1)
        assert_cables(1, expected)

    @check("Mode: Tied Bundle")
    def _():
        reset_scene()
        start, end = add_anchor((0, 0, 0)), add_anchor((5, 0, 0))
        select_only([start, end], start)
        run_op(bpy.ops.pcg.create_cable_bundle)
        assert_cables(settings.bundle_count, max(1, settings.middle_controls) + 2)

    def make_two_object_cable() -> bpy.types.Object:
        reset_scene()
        start, end = add_anchor((0, 0, 0)), add_anchor((4, 0, 2))
        select_only([start, end], start)
        run_op(bpy.ops.pcg.create_cable_from_selection)
        return cable_curves()[0]

    @check("Update: moving a CTRL empty reshapes the cable")
    def _():
        cable = make_two_object_cable()
        end_ctrl = dynamics.get_cable_controls(cable)[-1]
        end_ctrl.location.z += 1.5
        bpy.context.view_layer.update()
        bpy.context.scene.frame_set(bpy.context.scene.frame_current)
        curve_z = cable.data.splines[0].bezier_points[-1].co.z
        ctrl_z = end_ctrl.matrix_world.translation.z
        assert abs(curve_z - ctrl_z) < 1e-4, f"curve end z={curve_z:.4f}, control z={ctrl_z:.4f}"

    @check("Update: changing a cable's Thickness setting updates its bevel")
    def _():
        cable = make_two_object_cable()
        cable.pcg_dynamics.thickness = 0.037
        assert abs(cable.data.bevel_depth - 0.037) < 1e-6, f"bevel_depth is {cable.data.bevel_depth}"

    @check("Attach Controls: bone found from selection when no bone is active")
    def _():
        cable = make_two_object_cable()
        bpy.ops.object.armature_add(location=(0, 0, 0))
        rig = bpy.context.active_object
        bone_name = rig.data.bones[0].name
        rig.data.bones.active = None
        pose_bone = rig.pose.bones[bone_name]
        # Selection lives on PoseBone from 5.0 and on Bone before that.
        if hasattr(pose_bone, "select"):
            pose_bone.select = True
        else:
            pose_bone.bone.select = True
        ctrl = dynamics.get_cable_controls(cable)[0]
        ctrl.parent = None
        select_only([ctrl, rig], rig)
        run_op(bpy.ops.pcg.attach_control)
        assert ctrl.parent is rig and ctrl.parent_type == "BONE" and ctrl.parent_bone == bone_name, (
            f"parent={ctrl.parent}, type={ctrl.parent_type}, bone={ctrl.parent_bone!r}"
        )

    @check("Panel: draws without errors (no selection, cable, control empty)")
    def _():
        panel_cls = addon_module.PCG_PT_cable_panel
        cable = make_two_object_cable()
        states = [([], None), ([cable], cable)]
        ctrl = dynamics.get_cable_controls(cable)[1]
        states.append(([ctrl], ctrl))
        if dynamics.dynamics_supported():
            states.append(("dynamic", cable))
        for selection, active in states:
            if selection == "dynamic":
                select_only([cable], cable)
                run_op(bpy.ops.pcg.make_cable_dynamic)
                selection = [cable]
            select_only(selection, active)
            panel_cls.draw(_StubPanel(), bpy.context)
        return f"{len(states)} states drawn"

    if dynamics.dynamics_supported():

        @check("Dynamics: Make Dynamic, change Mass, Self Collision, Remove Dynamics cleans up")
        def _():
            cable = make_two_object_cable()
            objects_before = {o.name for o in bpy.data.objects}
            meshes_before = {m.name for m in bpy.data.meshes}
            select_only([cable], cable)

            run_op(bpy.ops.pcg.make_cable_dynamic)
            mod = cable.modifiers.get(dynamics.DYNAMICS_MODIFIER_NAME)
            assert mod is not None, "dynamics modifier not added"
            assert cable.pcg_dynamics.anchor_object is not None, "pin anchor helper not created"

            cable.pcg_dynamics.mass = 3.25
            value = dynamics._get_modifier_input(mod, "Mass")
            assert abs(value - 3.25) < 1e-6, f"modifier Mass input is {value}, expected 3.25"

            run_op(bpy.ops.pcg.enable_self_collision)
            assert cable.pcg_dynamics.selfcol_object is not None, "self-collision proxy not created"

            run_op(bpy.ops.pcg.remove_cable_dynamics)
            assert cable.modifiers.get(dynamics.DYNAMICS_MODIFIER_NAME) is None, "modifier left behind"
            leftover_objects = {o.name for o in bpy.data.objects} - objects_before
            leftover_meshes = {m.name for m in bpy.data.meshes} - meshes_before
            assert not leftover_objects, f"leftover objects: {sorted(leftover_objects)}"
            assert not leftover_meshes, f"leftover meshes: {sorted(leftover_meshes)}"
            assert cable.pcg_dynamics.anchor_object is None and cable.pcg_dynamics.selfcol_object is None

        @check("Colliders: Add Selected As Colliders works, and a failed asset load leaves nothing behind")
        def _():
            reset_scene()
            mesh = bpy.data.objects.new("PROP", bpy.data.meshes.new("PROP"))
            bpy.context.scene.collection.objects.link(mesh)
            select_only([mesh], mesh)

            # Simulate a Blender build whose bundled asset file lacks the Collider group.
            real_name = dynamics.COLLIDER_ASSET_GROUP_NAME
            dynamics.COLLIDER_ASSET_GROUP_NAME = "PCG Smoke Missing Group"
            try:
                bpy.ops.pcg.add_selected_colliders()
            except RuntimeError:
                pass  # the operator's ERROR report surfaces as RuntimeError when called from Python
            finally:
                dynamics.COLLIDER_ASSET_GROUP_NAME = real_name
            assert len(mesh.modifiers) == 0, f"modifiers left on mesh: {[m.name for m in mesh.modifiers]}"
            assert dynamics.COLLIDER_COLLECTION_NAME not in bpy.data.collections, "empty collider collection left"

            run_op(bpy.ops.pcg.add_selected_colliders)
            mod = mesh.modifiers.get(dynamics.COLLIDER_MODIFIER_NAME)
            assert mod is not None and mod.node_group is not None, "collider modifier not set up"
            assert mesh.name in bpy.data.collections[dynamics.COLLIDER_COLLECTION_NAME].objects

    else:

        @check("Dynamics: Make Dynamic")
        def _():
            return f"SKIP needs Blender {'.'.join(map(str, dynamics.DYNAMICS_MIN_BLENDER))}+"

        @check("Dynamics gate: tools disabled on this Blender version")
        def _():
            cable = make_two_object_cable()
            select_only([cable], cable)
            assert not bpy.ops.pcg.make_cable_dynamic.poll(), "Make Dynamic is enabled"
            mesh = bpy.data.objects.new("COLLIDER_TEST", bpy.data.meshes.new("COLLIDER_TEST"))
            bpy.context.scene.collection.objects.link(mesh)
            select_only([mesh], mesh)
            assert not bpy.ops.pcg.add_selected_colliders.poll(), "Add Selected As Colliders is enabled"

    @check("Disable add-on: no errors, no leftover classes or properties")
    def _():
        class_names = [cls.__name__ for cls in addon_module._CLASSES]
        errors: list[str] = []
        addon_utils.disable(ADDON_NAME, default_set=True, handle_error=lambda e: errors.append(str(e)))
        assert not errors, f"disable raised: {errors}"
        assert addon_utils.check(ADDON_NAME)[1] is False, "add-on still reported as loaded"
        assert not hasattr(bpy.types.Scene, "pcg_settings"), "Scene.pcg_settings still registered"
        assert not hasattr(bpy.types.Object, "pcg_dynamics"), "Object.pcg_dynamics still registered"
        lingering = [name for name in class_names if hasattr(bpy.types, name)]
        assert not lingering, f"classes still registered: {lingering}"
        assert not _op_registered("pcg.create_free_cable"), "pcg operators still registered"

    if staged_dir is not None:
        directories = bpy.context.preferences.filepaths.script_directories
        for entry in list(directories):
            if entry.name == "pcg_smoke":
                directories.remove(entry)
        shutil.rmtree(staged_dir, ignore_errors=True)

    return summarize()


class _StubLayout:
    """Stands in for UILayout, which only exists with a UI; lets Panel.draw run headless.

    It does not render anything, so it catches Python errors in draw code (bad attribute,
    missing property) but not layout or visual problems.
    """

    def __getattr__(self, name):
        def method(*args, **kwargs):
            if name == "prop":
                data, prop_name = args[0], args[1]
                assert prop_name in data.bl_rna.properties, f"layout.prop: no property {prop_name!r}"
            elif name == "operator":
                assert _op_registered(args[0]), f"layout.operator: unknown operator {args[0]!r}"
            return self

        return method


class _StubPanel:
    layout = _StubLayout()


def _op_registered(idname: str) -> bool:
    module, name = idname.split(".")
    try:
        getattr(getattr(bpy.ops, module), name).get_rna_type()
    except (AttributeError, KeyError):
        return False
    return True


def summarize() -> int:
    failed = [r for r in results if r[1] == "FAIL"]
    passed = sum(1 for r in results if r[1] == "PASS")
    skipped = sum(1 for r in results if r[1] == "SKIP")
    print(f"\n=== SUMMARY (Blender {bpy.app.version_string}): {passed} passed, {len(failed)} failed, {skipped} skipped ===")
    for name, _status, detail in failed:
        print(f"  FAIL: {name} - {detail}")
    print("RESULT:", "FAIL" if failed else "PASS", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
