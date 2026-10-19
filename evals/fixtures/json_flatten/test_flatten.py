"""Public original grader: flattening nested JSON."""

from hashlib import sha256
from pathlib import Path


HERE = Path(__file__).parent
OUT = HERE / "flat.txt"
INPUTS = {
    "config.json": "ac186fe89b866dac429af847b5a37bd047828d84f9cf407a60102c4ee52337a5",
}
EXPECTED = 'A.b=true\nA.z=1\ndb.host=localhost\ndb.password=null\ndb.replicas[0].host=r1\ndb.replicas[0].weight=0.5\ndb.replicas[1].host=r2\ndb.replicas[1].weight=2.25\nfeatures=[]\nlist[0]=10\nlist[10]=110\nlist[1]=20\nlist[2]=30\nlist[3]=40\nlist[4]=50\nlist[5]=60\nlist[6]=70\nlist[7]=80\nlist[8]=90\nlist[9]=100\nretries=3\nservice.debug=false\nservice.limits={}\nservice.name=billing\nservice.port=8080\nservice.tags[0]=a\nservice.tags[1]=b\nservice2[0][0]=1\nservice2[0][1]=2\nservice2[1][0]=3\n'


def _check_inputs():
    for name, digest in INPUTS.items():
        path = HERE / name
        assert path.is_file() and not path.is_symlink(), f"{name} must stay a regular file."
        assert sha256(path.read_bytes()).hexdigest() == digest, f"{name} must remain unchanged."


def _artifact():
    assert OUT.is_file() and not OUT.is_symlink(), "Create flat.txt as a regular file."
    return OUT.read_text()


def test_inputs_are_unchanged():
    _check_inputs()


def test_output_is_exact():
    _check_inputs()
    assert _artifact() == EXPECTED, "The output does not match the specified result."

