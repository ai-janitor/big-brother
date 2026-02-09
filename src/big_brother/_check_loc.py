"""Agents lose coherence past ~800 LOC. Tests are denser, so 500."""


def check_loc(rel, loc, args):
    is_test = "test" in rel.lower()
    limit = args.test_max if is_test else args.source_max
    if loc > limit:
        kind = "test" if is_test else "source"
        return ("loc", f"{rel}: {loc} lines ({kind}, limit {limit}, over by {loc - limit})")
    return None
