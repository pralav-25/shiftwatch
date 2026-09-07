"""Compare experiment outputs, allowing floating-point differences across BLAS builds."""

import json
import math
import sys


def compare(a, b, path="root"):
    if path == "root.environment":
        return  # Python patch and platform-dependent library metadata may differ.
    if isinstance(a, dict):
        assert a.keys() == b.keys(), path
        for key in a:
            compare(a[key], b[key], f"{path}.{key}")
    elif isinstance(a, list):
        assert len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            compare(x, y, f"{path}[{i}]")
    elif isinstance(a, float):
        assert math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-7), (path, a, b)
    else:
        assert a == b, (path, a, b)


if __name__ == "__main__":
    with open(sys.argv[1]) as left, open(sys.argv[2]) as right:
        compare(json.load(left), json.load(right))
    print("Report reproduced within numerical tolerance.")
