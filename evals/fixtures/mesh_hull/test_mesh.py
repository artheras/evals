"""Public original grader: the convex hull of a point cloud."""

from hashlib import sha256
import math
from pathlib import Path

import numpy as np
import trimesh


HERE = Path(__file__).parent
OUT = HERE / "hull.obj"
INPUTS = {
    "points.csv": "ef8a43d4d5362848694175395be4b540e3c5490669c7543cb27f2bb967fdcceb",
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
    assert OUT.is_file() and not OUT.is_symlink(), "Create hull.obj as a regular file."
    return load(OUT)


def assert_closed_solid(mesh):
    assert mesh.is_watertight, "The mesh must be closed: every edge shared by exactly two triangles."
    assert mesh.is_winding_consistent, "Neighbouring triangles must be wound consistently."
    assert mesh.volume > 0, "Triangles must face outward (counter-clockwise seen from outside)."


def test_inputs_are_unchanged():
    _check_inputs()


def test_it_is_the_convex_hull_of_the_points():
    mesh = submitted()
    assert_closed_solid(mesh)
    points = np.loadtxt(HERE / "points.csv", delimiter=",", skiprows=1)
    nearest = np.min(np.linalg.norm(mesh.vertices[:, None, :] - points[None, :, :], axis=2), axis=1)
    assert nearest.max() < 1e-5, "Every vertex of the hull must be one of the input points."
    normals = mesh.face_normals
    offsets = np.einsum("ij,ij->i", normals, mesh.vertices[mesh.faces[:, 0]])
    outside = points @ normals.T - offsets
    assert outside.max() < 1e-5, f"Every input point must be inside the hull; one is {outside.max():.4f} outside a face."

