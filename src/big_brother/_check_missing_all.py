"""Packages that re-export without __all__ break tab-completion
and make it impossible to know the public API from the outside."""

import ast


def check_missing_all(rel, full):
    try:
        with open(full) as f:
            source = f.read()
        tree = ast.parse(source, rel)
        has_reexports = any(
            isinstance(n, ast.ImportFrom) and n.names and not any(a.name == "*" for a in n.names)
            for n in ast.iter_child_nodes(tree)
        )
        has_all = any(
            isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
            for n in ast.iter_child_nodes(tree)
        )
        if has_reexports and not has_all:
            return ("structure", f"{rel}: re-exports without __all__")
    except (SyntaxError, OSError):
        pass
    return None
