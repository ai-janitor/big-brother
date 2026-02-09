"""The core law: 1 file, 1 unit of logic. When you `ls` a package,
each filename IS the API. Agents find logic by filename, not by
parsing AST. Output includes count AND LOC so the gatekeeper
can judge: 2 defs in 80 LOC = cohesive, 6 defs in 700 LOC = split it."""

import ast


def check_multi_fn(rel, full, loc):
    try:
        with open(full) as f:
            tree = ast.parse(f.read(), rel)
    except (SyntaxError, OSError):
        return None, None

    # Logic = public functions, async functions, and classes
    pub_logic = [
        n for n in ast.iter_child_nodes(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and not n.name.startswith("_")
    ]
    violation = None
    if len(pub_logic) > 1:
        names = [n.name for n in pub_logic]
        joined = ", ".join(names[:5])
        # Include line ranges so --lines can expand them
        fn_lines = [
            (n.name, n.lineno, getattr(n, "end_lineno", n.lineno))
            for n in pub_logic
        ]
        violation = ("multi-fn", f"{rel}: {len(pub_logic)} defs, {loc} LOC ({joined})", fn_lines)
    return violation, tree
