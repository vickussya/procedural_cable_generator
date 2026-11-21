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

"""Build the installable release ZIP.

    python tools/build_release.py

Writes dist/procedural_cable_generator-<version>.zip, with the version read from
bl_info in __init__.py. The ZIP holds a single top-level procedural_cable_generator/
folder with only the add-on's own files, which is what Blender's
Preferences > Add-ons > Install from Disk expects for a classic add-on. The folder
name must stay a valid Python module name (no dots, no version), or Blender can't
import it. README.md is left out: Blender doesn't use it, and it is read on GitHub.
"""

import ast
import sys
import zipfile
from pathlib import Path

PACKAGE_NAME = "procedural_cable_generator"
REPO_ROOT = Path(__file__).resolve().parent.parent
EXTRA_FILES = ("LICENSE",)

# A fixed timestamp makes rebuilding the same sources produce a byte-identical ZIP.
FIXED_DATE_TIME = (2026, 1, 1, 0, 0, 0)


def read_version() -> str:
    """Return bl_info["version"] as "X.Y.Z", parsed from __init__.py without importing bpy."""
    tree = ast.parse((REPO_ROOT / "__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "bl_info" for target in node.targets
        ):
            bl_info = ast.literal_eval(node.value)
            return ".".join(str(part) for part in bl_info["version"])
    raise SystemExit("bl_info not found in __init__.py")


def addon_files() -> list[Path]:
    """The add-on's own files: every top-level .py module plus LICENSE."""
    files = sorted(REPO_ROOT.glob("*.py"))
    for name in EXTRA_FILES:
        path = REPO_ROOT / name
        if not path.is_file():
            raise SystemExit(f"Missing required file: {name}")
        files.append(path)
    if REPO_ROOT / "__init__.py" not in files:
        raise SystemExit("Missing __init__.py")
    return files


def build() -> Path:
    version = read_version()
    dist = REPO_ROOT / "dist"
    dist.mkdir(exist_ok=True)
    zip_path = dist / f"{PACKAGE_NAME}-{version}.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in addon_files():
            info = zipfile.ZipInfo(f"{PACKAGE_NAME}/{path.name}", date_time=FIXED_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            # Store LF line endings (as git does), so a Windows checkout with CRLF files
            # builds the same ZIP as any other machine.
            archive.writestr(info, path.read_bytes().replace(b"\r\n", b"\n"))

    return zip_path


def main() -> int:
    zip_path = build()
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
    print(f"Built {zip_path.relative_to(REPO_ROOT)} ({zip_path.stat().st_size / 1024:.1f} KB, {len(names)} files):")
    for name in names:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
