#!/usr/bin/env python3
"""
Remove Python bytecode caches and common local tool artifacts from the repo.

Skips .git and top-level virtualenv folders (.venv, venv, env) so your
environment stays intact.

Usage:
  python scripts/clean.py
  python scripts/clean.py --dry-run
  python scripts/clean.py --only-bytecode
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_DEFAULT_ROOT = Path(__file__).resolve().parent.parent

_EXCLUDED_TOP_LEVEL = frozenset({".git", ".venv", "venv", "env"})

_CACHE_DIR_NAMES = frozenset({
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    ".tox",
})

_ROOT_ONLY_DIRS = frozenset({"dist", "build", ".eggs"})
_ROOT_FILES = frozenset({".coverage"})

# Whole trees removed via rmtree; do not list inner files in dry-run / second pass.
_TREE_REMOVED_DIR_NAMES = _CACHE_DIR_NAMES | frozenset({"__pycache__"})


def _is_excluded(path: Path, root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return True
    if not rel.parts:
        return False
    if rel.parts[0] in _EXCLUDED_TOP_LEVEL:
        return True
    if ".git" in rel.parts:
        return True
    return False


def _is_under_tree_removed_dir(path: Path, root: Path) -> bool:
    """True if path sits under a directory we delete wholesale (e.g. __pycache__)."""
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return True
    return any(part in _TREE_REMOVED_DIR_NAMES for part in rel.parts[:-1])


def _rm_tree(path: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"rm -r {path}")
    else:
        shutil.rmtree(path)


def _rm_file(path: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"rm {path}")
    else:
        path.unlink()


def _collect_cache_dirs(root: Path, extra: bool) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()

    for p in root.rglob("*"):
        if not p.is_dir() or _is_excluded(p, root):
            continue
        name = p.name
        if name == "__pycache__" or (extra and name in _CACHE_DIR_NAMES):
            rp = p.resolve()
            if rp not in seen:
                seen.add(rp)
                found.append(p)

    found.sort(key=lambda x: len(x.parts), reverse=True)
    return found


def _collect_bytecode_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file() or _is_excluded(p, root):
            continue
        if _is_under_tree_removed_dir(p, root):
            continue
        if p.suffix in (".pyc", ".pyo"):
            out.append(p)
        elif p.name.endswith(".py.class") or p.name == "$py.class":
            out.append(p)
    return out


def _collect_root_artifacts(root: Path, extra: bool) -> tuple[list[Path], list[Path]]:
    dirs: list[Path] = []
    files: list[Path] = []
    if not extra:
        return dirs, files
    for name in _ROOT_ONLY_DIRS:
        d = root / name
        if d.is_dir() and not _is_excluded(d, root):
            dirs.append(d)
    for name in _ROOT_FILES:
        f = root / name
        if f.is_file():
            files.append(f)
    try:
        for child in root.iterdir():
            if (
                child.is_dir()
                and not _is_excluded(child, root)
                and child.name.endswith(".egg-info")
            ):
                dirs.append(child)
    except OSError:
        pass
    return dirs, files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove __pycache__, *.pyc, and optional tool caches under the repository.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_DEFAULT_ROOT,
        help=f"Repository root (default: {_DEFAULT_ROOT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print paths that would be removed without deleting anything.",
    )
    parser.add_argument(
        "--only-bytecode",
        action="store_true",
        help="Only remove __pycache__ and .pyc/.pyo; keep pytest/mypy/ruff caches.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1

    extra = not args.only_bytecode
    dry = args.dry_run

    removed_dirs = 0
    removed_files = 0

    # Remove cache directories first so we do not try to unlink .pyc files twice.
    for d in _collect_cache_dirs(root, extra):
        _rm_tree(d, dry)
        removed_dirs += 1

    for f in _collect_bytecode_files(root):
        _rm_file(f, dry)
        removed_files += 1

    root_dirs, root_files = _collect_root_artifacts(root, extra)
    for d in root_dirs:
        _rm_tree(d, dry)
        removed_dirs += 1
    for f in root_files:
        _rm_file(f, dry)
        removed_files += 1

    action = "Would remove" if dry else "Removed"
    print(f"{action} {removed_dirs} director(y/ies) and {removed_files} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
