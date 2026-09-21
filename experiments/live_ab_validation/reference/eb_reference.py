"""eb_reference.py -- THE DECLARED EXTERNAL REFERENCE.

WHAT THIS IS.  A thin, isolated loader for the AUTHORS' empirical-Bernstein
running-mean confidence sequence, ``comparecast.confseq.confseq_eb``, vendored
verbatim by ``vendor.py`` at the commits the root's literature document pins.
It corresponds to Choe and Ramdas, *Comparing Sequential Forecasters*,
Theorem 2, whose target -- the time-varying average conditional score
difference -- is our target, the unweighted running conditional mean.

WHAT THIS IS NOT, and the guarantee is structural, not a promise.

  * It is NOT a construction in the primary panel.  ``vrun.CONSTRUCTIONS`` is
    ``(ADAPTER, CPREFIX, NAIVE)`` and this module never adds to it.
  * It NEVER overrides a decision.  Nothing here returns a decision, a tau, a
    gate state or a flag.  ``reference_bands`` returns two float arrays and
    nothing else, and ``assert_reference_cannot_decide`` makes that checkable.
  * The primary NEVER imports it.  The dependency runs one way only:
    reference -> primary.  ``vrun.py``, ``vgen.py``, ``vband.py`` and
    ``vcompare.py`` contain no import of this package, and
    ``tests_validation.py`` asserts that by reading their source.
  * It does not touch the frozen v1 results, ``cells.json``, ``PROTOCOL.md``
    or ``pinned/``.

THE TUNING IS FIXED BEFORE ANY COMPARISON AND CANNOT BE MOVED.  ``v_opt = 10``
(the authors' own default, frozen by them "after preliminary comparisons"),
``lo = -1.0``, ``hi = +1.0``, ``boundary_type = "mixture"``.  Three things the
coordinator prohibited are refused here rather than merely discouraged:
``v_opt=None`` (which would tune the boundary at the OBSERVED final variance,
i.e. after seeing the data), the one-sided forms without an explicit scale ``c``
(which would silently change the error budget and the direction), and any
partial-endpoint plug-in.  Each raises.

ALPHA.  The caller passes the existing two-sided per-gate allocation.
``confseq_eb`` itself performs the ``alpha/2`` split internally for the
two-sided call, so the value passed in is the per-gate allocation and NOT
half of it.  Passing a pre-halved alpha would silently double the error budget.

WHAT IS STILL UNMEASURED.  Whether this reference is tighter than the primary
at OUR n and OUR tie mass is NOT established by citing it, and this module
claims nothing about it.  The coordinator's own narrowing applies: adaptive
betting constructions do not all assume a common mean, and superiority at our
sample size is unproved.
"""

from __future__ import annotations

import importlib.util
import sys
import sysconfig
from pathlib import Path
from types import ModuleType
from typing import Optional, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
UPSTREAM = HERE / "upstream"
BUILD = HERE / "_build"
MANIFEST = HERE / "MANIFEST.json"

#: The frozen tuning.  Changing any of these is a protocol amendment, not a
#: parameter choice, and the comparison panel records them verbatim.
V_OPT = 10.0
LO = -1.0
HI = 1.0
BOUNDARY_TYPE = "mixture"

REFERENCE_LABEL = (
    "DECLARED REFERENCE (authors' code): comparecast.confseq.confseq_eb, "
    "Choe & Ramdas Comparing Sequential Forecasters Theorem 2, "
    "yjchoe/ComparingForecasters@52748c8 + gostevehoward/confseq@5ffe733, MIT. "
    "Reported beside the primary; never overrides any decision.")


class ReferenceUnavailable(RuntimeError):
    """The vendored reference could not be loaded.

    The coordinator's instruction is explicit: "Report import or resource
    failure rather than silently substituting another construction."  Every
    caller must let this propagate.  There is no fallback path in this module
    and adding one would defeat the purpose of an external reference.
    """


_CACHE: Optional[ModuleType] = None


def _load_package(name: str, init: Path, search: list) -> ModuleType:
    """Import a vendored package from an explicit location.

    ``submodule_search_locations`` is what lets the compiled ``boundaries``
    extension live in ``_build/`` while the package's ``__init__.py`` stays in
    the pristine verbatim ``upstream/`` tree: the package is one package with
    two search roots, and no byte of ``upstream/`` is written to or copied.
    """
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, init, submodule_search_locations=[str(p) for p in search])
    if spec is None or spec.loader is None:               # pragma: no cover
        raise ReferenceUnavailable(f"cannot build an import spec for {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def load_reference():
    """Import and return the authors' ``confseq_eb``, or raise.

    Raises ``ReferenceUnavailable`` -- never substitutes, never degrades.
    """
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    ext = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    so = BUILD / f"boundaries{ext}"
    if not so.exists():
        raise ReferenceUnavailable(
            f"the authors' compiled boundary module is not built for this "
            f"interpreter: {so} is missing. Rebuild with reference/vendor.py "
            f"(it needs Boost headers and pybind11). Report this resource "
            f"failure rather than substituting another construction.")
    for probe in (UPSTREAM / "confseq" / "__init__.py",
                  UPSTREAM / "comparecast" / "confseq.py",
                  UPSTREAM / "comparecast" / "utils.py"):
        if not probe.exists():
            raise ReferenceUnavailable(
                f"the vendored tree is incomplete: {probe} is missing. "
                f"Re-run reference/vendor.py.")
    try:
        _load_package("confseq", UPSTREAM / "confseq" / "__init__.py",
                      [UPSTREAM / "confseq", BUILD])
        _load_package("comparecast", UPSTREAM / "comparecast" / "__init__.py",
                      [UPSTREAM / "comparecast"])
        from comparecast.confseq import confseq_eb        # type: ignore
    except ReferenceUnavailable:
        raise
    except BaseException as exc:                          # noqa: BLE001
        raise ReferenceUnavailable(
            f"importing the vendored authors' reference failed: {exc!r}. "
            f"Report this import failure; do not substitute.") from exc
    _CACHE = confseq_eb
    return confseq_eb


def reference_available() -> bool:
    """``True`` if the reference imports.  Used only to REPORT availability."""
    try:
        load_reference()
        return True
    except ReferenceUnavailable:
        return False


def reference_bands(z: np.ndarray, alpha: float) -> Tuple[np.ndarray, np.ndarray]:
    """The authors' two-sided EB confidence sequence on the score prefix ``z``.

    ``z`` are the bounded latent scores in enrollment order, in ``[-1, +1]``.
    ``alpha`` is the existing two-sided PER-GATE allocation; ``confseq_eb``
    applies its own ``alpha/2`` split, so do not pre-halve it.

    Returns ``(lcbs, ucbs)``: element ``i`` is the interval for the running
    mean of ``z[:i+1]``.  It returns bands and nothing else -- no decision, no
    tau, no flag -- because a reference that could emit a decision could
    override one.
    """
    z = np.asarray(z, dtype=np.float64)
    if z.ndim != 1:
        raise ValueError("z must be one-dimensional")
    if z.size == 0:
        return np.zeros(0), np.zeros(0)
    if not np.all(np.isfinite(z)):
        raise ValueError("z contains non-finite values")
    if float(z.min()) < LO or float(z.max()) > HI:
        raise ValueError(
            f"scores must lie in [{LO}, {HI}] for the declared range; got "
            f"[{z.min()}, {z.max()}]. The range is part of the frozen tuning.")
    if not (0.0 < float(alpha) < 1.0):
        raise ValueError(f"alpha must be in (0,1); got {alpha}")
    confseq_eb = load_reference()
    cs = confseq_eb(z, alpha=float(alpha), lo=LO, hi=HI,
                    boundary_type=BOUNDARY_TYPE, v_opt=V_OPT)
    lcbs = np.asarray(cs.lcbs, dtype=np.float64)
    ucbs = np.asarray(cs.ucbs, dtype=np.float64)
    if lcbs.shape != z.shape or ucbs.shape != z.shape:    # pragma: no cover
        raise ReferenceUnavailable(
            "the reference returned bands of unexpected shape; refusing to use it")
    return lcbs, ucbs


def assert_reference_cannot_decide() -> None:
    """Structural check that this module cannot influence a decision.

    Checked rather than asserted in prose: the public surface returns arrays,
    the primary's construction tuple is untouched, and the primary's source
    contains no import of this package.
    """
    import vrun                                            # the primary

    if "reference" in getattr(vrun, "CONSTRUCTIONS", ()):  # pragma: no cover
        raise AssertionError("the reference entered vrun.CONSTRUCTIONS")
    if len(vrun.CONSTRUCTIONS) != 3:                       # pragma: no cover
        raise AssertionError(
            f"the primary panel changed size: {vrun.CONSTRUCTIONS}")
    primary_sources = ("vrun.py", "vgen.py", "vband.py", "vcompare.py",
                       "vfixtures.py", "vlastlook_check.py")
    for name in primary_sources:
        text = (HERE.parent / name).read_text()
        for forbidden in ("from reference", "import reference",
                          "eb_reference", "confseq_eb"):
            if forbidden in text:                          # pragma: no cover
                raise AssertionError(
                    f"{name} references the external reference ({forbidden!r}); "
                    f"the primary must not import it")


if __name__ == "__main__":
    ok = reference_available()
    print(REFERENCE_LABEL)
    print(f"import: {'OK' if ok else 'FAILED'}")
    if ok:
        rng = np.random.default_rng(12345)
        z = rng.choice([-1.0, 0.0, 1.0], size=200, p=[0.2, 0.6, 0.2])
        lo, hi = reference_bands(z, alpha=0.00625)
        print(f"n=200  running mean {z.mean():+.6f}  "
              f"band [{lo[-1]:+.6f}, {hi[-1]:+.6f}]  width {hi[-1]-lo[-1]:.6f}")
    else:
        raise SystemExit(2)
