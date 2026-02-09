"""The core law: 1 file, 1 public function. When you `ls` a package,
each filename IS the API. Agents find functions by filename, not by
parsing AST. Output includes fn count AND LOC so the gatekeeper
can judge: 2 fns in 80 LOC = cohesive, 6 fns in 700 LOC = split it."""

import ast


def check_multi_fn(rel, full, loc):
    try:
        with open(full) as f:
            tree = ast.parse(f.read(), rel)
    except (SyntaxError, OSError):
        return None, None

    pub_fns = [
        n for n in ast.iter_child_nodes(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not n.name.startswith("_")
    ]
    violation = None
    if len(pub_fns) > 1:
        names = [n.name for n in pub_fns]
        joined = ", ".join(names[:5])
        # Include line ranges so --lines can expand them
        fn_lines = [
            (n.name, n.lineno, getattr(n, "end_lineno", n.lineno))
            for n in pub_fns
        ]
        violation = ("multi-fn", f"{rel}: {len(pub_fns)} fns, {loc} LOC ({joined})", fn_lines)
    return violation, tree
