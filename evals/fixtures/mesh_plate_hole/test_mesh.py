"""Public original grader: a plate with a cylindrical through-hole."""

from hashlib import sha256
import math
from pathlib import Path

import numpy as np
import trimesh


HERE = Path(__file__).parent
OUT = HERE / "plate.obj"
INPUTS = {
    "spec.json": "76ae4f19adfde244f46b63f67d99160a90bb0b0a062cf6c6c2ad91e2e785a386",
}
SIZE = (60.0, 40.0, 5.0)
CENTRE = (30.0, 20.0)
RADIUS = 5.0
SEGMENTS = 32


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
    assert OUT.is_file() and not OUT.is_symlink(), "Create plate.obj as a regular file."
    return load(OUT)


def assert_closed_solid(mesh):
    assert mesh.is_watertight, "The mesh must be closed: every edge shared by exactly two triangles."
    assert mesh.is_winding_consistent, "Neighbouring triangles must be wound consistently."
    assert mesh.volume > 0, "Triangles must face outward (counter-clockwise seen from outside)."


def test_inputs_are_unchanged():
    _check_inputs()


def test_the_plate_has_one_round_through_hole():
    mesh = submitted()
    assert_closed_solid(mesh)
    assert np.allclose(mesh.bounds, [[0, 0, 0], list(SIZE)], atol=1e-6), f"Bounds are {mesh.bounds.tolist()}."
    assert mesh.euler_number == 0, f"One hole straight through the plate gives Euler number 0; this mesh has {mesh.euler_number}."
    removed = (SIZE[0] * SIZE[1] * SIZE[2] - mesh.volume) / SIZE[2]
    smallest = SEGMENTS / 2 * RADIUS ** 2 * math.sin(2 * math.pi / SEGMENTS)
    assert smallest - 1e-6 <= removed <= math.pi * RADIUS ** 2 + 1e-6, f"The hole's cross-section is {removed:.3f} mm^2."
    distance = np.hypot(mesh.vertices[:, 0] - CENTRE[0], mesh.vertices[:, 1] - CENTRE[1])
    assert distance.min() >= RADIUS - 1e-6, "No part of the plate may reach inside the hole's circle."

