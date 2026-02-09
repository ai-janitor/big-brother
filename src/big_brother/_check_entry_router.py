"""Entry files should route to functions defined elsewhere.
When they accumulate logic, they become monoliths that are
hard to test and impossible to import from."""

import fnmatch

from big_brother._laws import ENTRY_PATTERNS


def check_entry_router(rel, basename, tree):
    is_entry = any(fnmatch.fnmatch(basename, pat) for pat in ENTRY_PATTERNS)
    if not is_entry:
        return None
    defs = [
        n for n in tree.body
        if hasattr(n, 'name')
    ]
    non_main = [d for d in defs if d.name != "main"]
    if len(non_main) > 3:
        names_list = [d.name for d in non_main[:5]]
        return ("entry", f"{rel}: {len(non_main)} defs in entry file ({', '.join(names_list)})")
    return None
