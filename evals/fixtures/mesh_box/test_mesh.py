"""Public original grader: a box with exact dimensions and placement."""

from hashlib import sha256
import math
from pathlib import Path

import numpy as np
import trimesh


HERE = Path(__file__).parent
OUT = HERE / "box.obj"
INPUTS = {
    "spec.json": "d26b073af6be81e1c0b14e5e3c8419c8eefd47397c25e8a41103621debe691b3",
}
SIZE = (40.0, 20.0, 10.0)


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
    assert OUT.is_file() and not OUT.is_symlink(), "Create box.obj as a regular file."
    return load(OUT)


def assert_closed_solid(mesh):
    assert mesh.is_watertight, "The mesh must be closed: every edge shared by exactly two triangles."
    assert mesh.is_winding_consistent, "Neighbouring triangles must be wound consistently."
    assert mesh.volume > 0, "Triangles must face outward (counter-clockwise seen from outside)."


def test_inputs_are_unchanged():
    _check_inputs()


def test_the_box_has_the_specified_size_and_place():
    mesh = submitted()
    assert_closed_solid(mesh)
    assert np.allclose(mesh.bounds, [[0, 0, 0], list(SIZE)], atol=1e-6), f"Bounds are {mesh.bounds.tolist()}."
    assert math.isclose(mesh.volume, SIZE[0] * SIZE[1] * SIZE[2], rel_tol=1e-9), f"Volume is {mesh.volume}."

