"""Public original grader: convert a mesh from inches to millimetres and place it on the build plate."""

from hashlib import sha256
import math
from pathlib import Path

import numpy as np
import trimesh


HERE = Path(__file__).parent
OUT = HERE / "bracket_mm.obj"
INPUTS = {
    "bracket_in.obj": "e1ee6bdcbb48c30972c8f06485d02bcfbe7275594e60d636e29599b38527deaf",
}



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
    assert OUT.is_file() and not OUT.is_symlink(), "Create bracket_mm.obj as a regular file."
    return load(OUT)


def assert_closed_solid(mesh):
    assert mesh.is_watertight, "The mesh must be closed: every edge shared by exactly two triangles."
    assert mesh.is_winding_consistent, "Neighbouring triangles must be wound consistently."
    assert mesh.volume > 0, "Triangles must face outward (counter-clockwise seen from outside)."


def test_inputs_are_unchanged():
    _check_inputs()


def test_it_is_the_same_part_in_millimetres_on_the_plate():
    mesh = submitted()
    assert_closed_solid(mesh)
    original = load(HERE / "bracket_in.obj")
    expected = original.vertices * 25.4
    expected = expected - [(expected[:, 0].min() + expected[:, 0].max()) / 2,
                           (expected[:, 1].min() + expected[:, 1].max()) / 2, expected[:, 2].min()]
    assert len(mesh.faces) == len(original.faces), "Keep the same triangles; only move and scale the part."
    assert len(mesh.vertices) == len(expected), "Keep the same vertices; only move and scale the part."
    got = mesh.vertices[np.lexsort(np.round(mesh.vertices, 4).T[::-1])]
    want = expected[np.lexsort(np.round(expected, 4).T[::-1])]
    assert np.allclose(got, want, atol=1e-4), "The vertices are not the original part scaled to millimetres and placed as asked."
    assert math.isclose(mesh.volume, original.volume * 25.4 ** 3, rel_tol=1e-6), "The volume does not match the scaled part."

