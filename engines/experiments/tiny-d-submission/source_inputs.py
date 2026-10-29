"""Pure source-name contract for scalar D experiment snapshots.

The readable board is a template. A snapshot must retain that template, the
recipe, every named shared fragment and the pinned assembler before executing
source.prepare(). The latter still verifies their bytes and the assembled
board digest; this module neither assembles C nor admits a native image.
"""
import re

D = "engines/experiments/tiny-d-submission/"
ENTRY = "engines/compact/tiny-entry-d/"
RECIPE = ENTRY + "recipe.json"
SELF = D + "source_inputs.py"
COMPOSER = "engines/scripts/source_composition.py"
NATIVE = ("tiny.h", "board.c", "search.c", "runtime.c", "start.S", "image.ld")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_SHARED = re.compile(r"engines/common/[a-z][a-z0-9_]*\.c\Z")


def _pins(values):
    if not isinstance(values, dict) or not values or any(
            not isinstance(name, str) or not isinstance(digest, str)
            or not _DIGEST.fullmatch(digest) for name, digest in values.items()):
        raise ValueError("named recipe source SHA-256 pins required")
    return values


def source_names(recipe):
    """Names needed by actual scalar source preparation, without HQ/loader code."""
    native = _pins(recipe.get("native_source_sha256"))
    if any("native/" + name not in native for name in NATIVE):
        raise ValueError("complete scalar D native recipe inputs required")
    shipping = _pins(recipe.get("shipping_source_sha256"))
    if "shipping_fused_ray.py" not in shipping:
        raise ValueError("scalar D source transform recipe pin required")
    shared = _pins(recipe.get("shared_source_sha256"))
    if any(not _SHARED.fullmatch(name) for name in shared):
        raise ValueError("shared source names must belong to engines/common")
    helpers = _pins(recipe.get("helper_sha256"))
    if set(helpers) != {COMPOSER}:
        raise ValueError("exact scalar D source assembler required")
    assembled = _pins(recipe.get("assembled_source_sha256"))
    if set(assembled) != {"native/board.c"}:
        raise ValueError("assembled scalar D board recipe pin required")
    return tuple(ENTRY + "native/" + name for name in NATIVE) + (
        RECIPE, ENTRY + "shipping_fused_ray.py", "engines/scripts/production.py",
        D + "source.py", *sorted(shared), *sorted(helpers))


def producer_names(recipe):
    """Exact input closure of build.py's unreduced prefix storage control.

    Snapshot-only helpers such as this module belong to each experiment's
    separate tools, not to the maintained producer's input identity.
    """
    return source_names(recipe) + (
        ENTRY + "packer.py", "engines/experiments/tcec-scope/build.py",
        "engines/scripts/minify.py", "engines/scripts/rename_c.py",
        D + "build.py", D + "packaging.py", D + "storage.py")
