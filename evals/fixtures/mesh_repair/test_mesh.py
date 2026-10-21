"""Public original grader: repair a scanned mesh with a hole and inconsistent winding."""

from hashlib import sha256
import math
from pathlib import Path

import numpy as np
import trimesh


HERE = Path(__file__).parent
OUT = HERE / "fixed.obj"
INPUTS = {
    "broken.obj": "1f30576c92ab22fdd2b491d93acf334ea1ce25f51a3353ec808482ba0be3c51d",
}
EXPECTED_VOLUME = 6322.2546963090135
EXPECTED_FACES = 80


def _check_inputs():
    for name, digest in INPUTS.items():
        path = HERE / name
        assert path.is_file() and not path.is_symlink(), f"{name} must stay a regular file."
        assert sha256(path.read_bytes()).hexdigest() == digest, f"{name} must remain unchanged."


def load(path):
    """An OBJ file as one mesh, with coincident vertices merged and nothing else repaired."""
    try:
        mesh = trimesh.load(path, file_type="obj", force="mesh", process=True)
    except Exception as error:
        raise AssertionError(f"{path.name} must be a readable OBJ mesh: {error}") from error
    assert isinstance(mesh, trimesh.Trimesh) and len(mesh.faces) > 0, f"{path.name} must contain triangles."
    return mesh


def submitted():
    _check_inputs()
    assert OUT.is_file() and not OUT.is_symlink(), "Create fixed.obj as a regular file."
    return load(OUT)


def assert_closed_solid(mesh):
    assert mesh.is_watertight, "The mesh must be closed: every edge shared by exactly two triangles."
    assert mesh.is_winding_consistent, "Neighbouring triangles must be wound consistently."
    assert mesh.volume > 0, "Triangles must face outward (counter-clockwise seen from outside)."


def test_inputs_are_unchanged():
    _check_inputs()


def test_the_mesh_is_a_repaired_closed_solid():
    mesh = submitted()
    assert_closed_solid(mesh)
    original = load(HERE / "broken.obj")
    nearest = np.min(np.linalg.norm(mesh.vertices[:, None, :] - original.vertices[None, :, :], axis=2), axis=1)
    assert nearest.max() < 1e-6 and len(mesh.vertices) == len(original.vertices), "Keep the original vertices; add none."
    assert len(mesh.faces) == EXPECTED_FACES, f"The repaired mesh should have {EXPECTED_FACES} triangles, it has {len(mesh.faces)}."
    assert math.isclose(mesh.volume, EXPECTED_VOLUME, rel_tol=1e-9), f"Volume {mesh.volume:.6f}, expected {EXPECTED_VOLUME:.6f}."

