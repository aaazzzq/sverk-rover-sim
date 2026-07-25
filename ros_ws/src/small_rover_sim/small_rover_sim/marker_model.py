"""Build a rover SDF with an optional, runtime-configured ArUco marker."""

from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_prefix


def _element(parent, tag, text=None, **attributes):
    child = ET.SubElement(parent, tag, attributes)
    if text is not None:
        child.text = str(text)
    return child


def _material(parent, value):
    material = _element(parent, "material")
    _element(material, "ambient", value)
    _element(material, "diffuse", value)
    _element(material, "specular", "0 0 0 1")


def _marker_bits(vocabulary, marker_id):
    prefix = Path(get_package_prefix("small_rover_marker_tools"))
    executable = prefix / "lib" / "small_rover_marker_tools" / "aruco_marker_bits"
    result = subprocess.run(
        [str(executable), vocabulary, str(marker_id)],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = [row.strip() for row in result.stdout.splitlines() if row.strip()]
    if not rows or any(len(row) != len(rows) or set(row) - {"0", "1"} for row in rows):
        raise RuntimeError("ArUco marker helper returned an invalid bit matrix")
    return rows


def create_marker_model(
    source_path,
    entity_name,
    marker_size,
    vocabulary,
    marker_id,
    marker_x,
    marker_y,
    marker_z,
    marker_yaw,
):
    """Return a temporary SDF path containing a fixed marker link."""
    if marker_size <= 0:
        raise ValueError("marker_size must be greater than zero")

    rows = _marker_bits(vocabulary, marker_id)
    tree = ET.parse(source_path)
    model = tree.getroot().find("model")
    if model is None:
        raise RuntimeError(f"No <model> element found in {source_path}")

    link = _element(model, "link", name="aruco_marker_link")
    _element(
        link,
        "pose",
        f"{marker_x:.9g} {marker_y:.9g} {marker_z:.9g} 0 0 {marker_yaw:.9g}",
        relative_to="base_link",
    )
    inertial = _element(link, "inertial")
    _element(inertial, "mass", "0.002")
    inertia = _element(inertial, "inertia")
    _element(inertia, "ixx", "0.000001")
    _element(inertia, "iyy", "0.000001")
    _element(inertia, "izz", "0.000001")

    module_count = len(rows)
    module_size = marker_size / module_count
    board_size = marker_size + 2.0 * module_size

    board = _element(link, "visual", name="aruco_marker_backing")
    _element(board, "pose", "0 0 0.00025 0 0 0")
    board_geometry = _element(board, "geometry")
    board_box = _element(board_geometry, "box")
    _element(board_box, "size", f"{board_size:.9g} {board_size:.9g} 0.0005")
    _material(board, "1 1 1 1")

    half_size = marker_size / 2.0
    for row_index, row in enumerate(rows):
        for col_index, bit in enumerate(row):
            if bit != "0":
                continue
            cell = _element(
                link,
                "visual",
                name=f"aruco_marker_black_{row_index}_{col_index}",
            )
            x = half_size - (row_index + 0.5) * module_size
            y = half_size - (col_index + 0.5) * module_size
            _element(cell, "pose", f"{x:.9g} {y:.9g} 0.0006 0 0 0")
            cell_geometry = _element(cell, "geometry")
            cell_box = _element(cell_geometry, "box")
            _element(
                cell_box,
                "size",
                f"{module_size:.9g} {module_size:.9g} 0.0002",
            )
            _material(cell, "0 0 0 1")

    joint = _element(model, "joint", name="aruco_marker_joint", type="fixed")
    _element(joint, "parent", "base_link")
    _element(joint, "child", "aruco_marker_link")

    safe_entity = re.sub(r"[^A-Za-z0-9_.-]", "_", entity_name)
    output_dir = Path("/tmp/small_rover_models")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (
        f"{safe_entity}-{vocabulary}-{marker_id}-{marker_size:.6g}.sdf"
    )
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return str(output_path)
