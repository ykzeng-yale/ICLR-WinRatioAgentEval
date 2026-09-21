"""NOT AUTHOR CODE -- a vendor shim written for this repository.

The upstream ``comparecast/__init__.py`` star-imports eleven sibling modules and
so requires pandas, matplotlib and seaborn at import time. The reference needs
exactly two upstream modules, ``comparecast.confseq`` and ``comparecast.utils``,
which between them import only numpy and typing.

This file is therefore intentionally empty of behaviour. It exists so that
``from comparecast.utils import check_bounds`` -- the import statement inside the
authors' unmodified ``confseq.py`` -- resolves. The upstream initialiser's own
SHA-256 is recorded in MANIFEST.json under ``verified_not_vendored``.
"""
