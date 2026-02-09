"""Walk the project tree, apply every check, sort into buckets.  # bb:vetted

The scanner sees everything but judges nothing. Each file gets
inspected against every law. The bb:vetted mark determines which
bucket (violations vs vetted) — not whether the check runs.
"""

import fnmatch
import os

from big_brother._laws import SKIP_DIRS
from big_brother._check_loc import check_loc
from big_brother._check_missing_all import check_missing_all
from big_brother._check_multi_fn import check_multi_fn
from big_brother._check_entry_router import check_entry_router


def _file_loc(full):
    """Count lines in a file."""
    try:
        with open(full) as f:
            return sum(1 for _ in f)
    except (OSError, UnicodeDecodeError):
        return 0


def _is_vetted(full):
    """Check if the gatekeeper has reviewed and approved this file.

    The mark belongs near the top — usually in the module docstring.
    Only the first 10 lines are scanned so it can't hide mid-file.
    """
    try:
        with open(full) as f:
            for _, line in zip(range(10), f):
                if "bb:vetted" in line:
                    return True
    except (OSError, UnicodeDecodeError):
        pass
    return False


def scan(root, args):
    """Walk every .py file under root, return (violations, vetted).

    Both lists contain (rule, detail) tuples. The only difference
    is whether the file carried bb:vetted — the checks are identical.
    """
    violations = []
    vetted = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            if any(fnmatch.fnmatch(fname, pat) for pat in args.ignore):
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)
            if any(fnmatch.fnmatch(rel, pat) for pat in args.ignore):
                continue

            loc = _file_loc(full)
            basename = os.path.basename(rel)
            bucket = vetted if _is_vetted(full) else violations

            loc_v = check_loc(rel, loc, args)
            if loc_v:
                bucket.append(loc_v)

            # __init__.py only gets LOC + __all__ checks — multi-fn is expected.
            if basename == "__init__.py":
                all_v = check_missing_all(rel, full)
                if all_v:
                    bucket.append(all_v)
                continue

            # Test files only get LOC checks — multi-fn is normal in tests.
            if "test" in rel.lower():
                continue

            multi_v, tree = check_multi_fn(rel, full, loc)
            if multi_v:
                bucket.append(multi_v)
            if tree is None:
                continue

            entry_v = check_entry_router(rel, basename, tree)
            if entry_v:
                bucket.append(entry_v)

    return violations, vetted
