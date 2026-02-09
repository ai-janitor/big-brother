"""Extract public functions from a file into a 1-file-1-function package.

Reads the source, uses AST to identify public functions and their
dependencies (imports, constants, private helpers), then writes each
function to its own file with only the imports it needs.

Auto-fixes:
- Cross-imports between sibling public functions
- Shared helpers extracted to _helpers.py (no duplication)
- SCRIPT_DIR depth adjustment for package nesting
"""

import ast
import os
import re
import sys


def stub(source_path, output_dir=None):
    """The single entry point — read source, write package."""
    source_path = os.path.abspath(source_path)
    if not os.path.isfile(source_path):
        print(f"Error: {source_path} not found")
        sys.exit(1)

    with open(source_path) as f:
        source = f.read()
    lines = source.splitlines(keepends=True)

    try:
        tree = ast.parse(source, source_path)
    except SyntaxError as e:
        print(f"Error: cannot parse {source_path}: {e}")
        sys.exit(1)

    if output_dir is None:
        base = os.path.splitext(source_path)[0]
        output_dir = base
    output_dir = os.path.abspath(output_dir)

    pub_fns = _find_public_functions(tree)
    if len(pub_fns) <= 1:
        print(f"{source_path}: only {len(pub_fns)} public function(s), nothing to stub")
        return

    priv_fns = _find_private_functions(tree)
    imports = _find_imports(tree)
    constants = _find_constants(tree)
    module_doc = ast.get_docstring(tree)

    # Map each name to the set of names it references
    all_nodes = pub_fns + priv_fns + constants
    name_refs = {}
    for node in all_nodes:
        name_refs[node.name if hasattr(node, 'name') else _const_name(node)] = _names_used(node)

    import_names = _import_provided_names(imports)

    all_pub_names = [fn.name for fn in pub_fns]

    # --- Pass 1: compute deps for all functions, identify shared helpers ---
    fn_deps = {}  # fname -> {privates, constants, imports, sibling_refs}
    helper_usage = {}  # helper_name -> [pub_fn_names that need it]

    for fn_node in pub_fns:
        fname = fn_node.name
        needed_privates = _transitive_deps(fname, name_refs, priv_fns)
        all_ref_names = set(name_refs.get(fname, set()))
        for p in needed_privates:
            all_ref_names |= name_refs.get(p.name, set())
        needed_constants = _transitive_constants(constants, name_refs, all_ref_names)
        for c in needed_constants:
            all_ref_names |= name_refs.get(_const_name(c), set())
        needed_imports = _filter_imports(imports, import_names, all_ref_names)

        # Cross-import detection: sibling public fns this function references
        sibling_refs = name_refs.get(fname, set()) & set(all_pub_names) - {fname}

        fn_deps[fname] = {
            'node': fn_node,
            'privates': needed_privates,
            'constants': needed_constants,
            'imports': needed_imports,
            'all_ref_names': all_ref_names,
            'sibling_refs': sibling_refs,
        }

        # Track which helpers are used by which public functions
        for p in needed_privates:
            helper_usage.setdefault(p.name, []).append(fname)

    # Partition helpers: shared (2+ users) vs colocated (1 user)
    shared_helpers = {name for name, users in helper_usage.items() if len(users) > 1}
    shared_helper_nodes = [n for n in priv_fns if n.name in shared_helpers]

    # Report tracking
    report = _StubReport()

    os.makedirs(output_dir, exist_ok=True)

    # --- Write _helpers.py if there are shared helpers ---
    if shared_helper_nodes:
        _write_helpers_file(
            output_dir, shared_helper_nodes, name_refs, constants,
            imports, import_names, lines, module_doc, source_path, report,
        )

    # --- Pass 2: write function files ---
    written_files = []

    for fn_node in pub_fns:
        fname = fn_node.name
        deps = fn_deps[fname]

        # Split privates into colocated vs imported-from-helpers
        colocated_privates = [p for p in deps['privates'] if p.name not in shared_helpers]
        imported_helpers = [p.name for p in deps['privates'] if p.name in shared_helpers]

        # Recompute imports: need to include names from colocated privates only
        # (shared helpers bring their own imports in _helpers.py)
        all_ref_names = set(name_refs.get(fname, set()))
        for p in colocated_privates:
            all_ref_names |= name_refs.get(p.name, set())
        for c in deps['constants']:
            all_ref_names |= name_refs.get(_const_name(c), set())
        needed_imports = _filter_imports(imports, import_names, all_ref_names)

        out_lines = []
        # Module context as comment
        if module_doc:
            first_line = module_doc.split('\n')[0]
            out_lines.append(f'# From: {os.path.basename(source_path)} — {first_line}\n')
        out_lines.append('\n')

        # External imports
        for imp_node in needed_imports:
            out_lines.append(_node_source(imp_node, lines))

        if needed_imports:
            out_lines.append('\n')

        # Cross-imports from sibling public functions
        sibling_imports = sorted(deps['sibling_refs'])
        if sibling_imports:
            for sib in sibling_imports:
                out_lines.append(f'from .{sib} import {sib}\n')
                report.cross_imports.append((fname, sib))
            out_lines.append('\n')

        # Imports from _helpers.py
        if imported_helpers:
            helper_names = sorted(imported_helpers)
            out_lines.append(f'from ._helpers import {", ".join(helper_names)}\n')
            out_lines.append('\n')

        # Constants (with SCRIPT_DIR depth fix)
        for const_node in deps['constants']:
            const_src = _node_source(const_node, lines)
            const_src = _fix_script_dir_depth(const_src)
            if const_src != _node_source(const_node, lines):
                cname = _const_name(const_node)
                report.script_dir_fixes.append(fname)
            out_lines.append(const_src)

        if deps['constants']:
            out_lines.append('\n')

        # Colocated private helpers (single-use only)
        for priv_node in colocated_privates:
            out_lines.append('\n')
            out_lines.append(_node_source(priv_node, lines))

        if colocated_privates:
            out_lines.append('\n')

        # The function itself
        out_lines.append('\n')
        out_lines.append(_node_source(fn_node, lines))

        out_path = os.path.join(output_dir, f"{fname}.py")
        with open(out_path, 'w') as f:
            content = ''.join(out_lines)
            while '\n\n\n\n' in content:
                content = content.replace('\n\n\n\n', '\n\n\n')
            f.write(content)
        written_files.append(fname)
        print(f"  {fname}.py")

    # --- __init__.py ---
    init_lines = []
    if module_doc:
        init_lines.append(f'"""{module_doc}"""\n\n')
    for name in all_pub_names:
        init_lines.append(f"from .{name} import {name}\n")
    init_lines.append(f"\n__all__ = {all_pub_names!r}\n")

    with open(os.path.join(output_dir, "__init__.py"), 'w') as f:
        f.write(''.join(init_lines))
    print("  __init__.py")

    # --- __main__.py if there's a main() function ---
    if "main" in all_pub_names:
        pkg_name = os.path.splitext(os.path.basename(source_path))[0]
        main_lines = [
            f'"""python3 -m {pkg_name} — run the module."""\n',
            '\n',
            f'from {pkg_name} import main\n',
            '\n',
            'main()\n',
        ]
        with open(os.path.join(output_dir, "__main__.py"), 'w') as f:
            f.write(''.join(main_lines))
        print("  __main__.py")

    # --- Detect subprocess calls referencing original filename ---
    basename = os.path.splitext(os.path.basename(source_path))[0]
    for fn_node in pub_fns:
        fn_src = _node_source(fn_node, lines)
        if f'sys.executable' in fn_src and basename in fn_src:
            report.subprocess_refs.append(fn_node.name)
        elif f"python3 {basename}" in fn_src or f"python {basename}" in fn_src:
            report.subprocess_refs.append(fn_node.name)

    # --- Post-stub report ---
    report.shared_helper_names = [n.name for n in shared_helper_nodes]
    report.print_report(len(written_files), output_dir, basename)


def _find_public_functions(tree):
    return [
        n for n in ast.iter_child_nodes(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not n.name.startswith("_")
    ]


def _find_private_functions(tree):
    return [
        n for n in ast.iter_child_nodes(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name.startswith("_")
    ]


def _find_imports(tree):
    return [
        n for n in ast.iter_child_nodes(tree)
        if isinstance(n, (ast.Import, ast.ImportFrom))
    ]


def _find_constants(tree):
    """Module-level assignments that look like constants or config."""
    result = []
    for n in ast.iter_child_nodes(tree):
        if isinstance(n, ast.Assign):
            # Skip __all__, __doc__ etc
            names = [t.id for t in n.targets if isinstance(t, ast.Name)]
            if any(name.startswith("__") and name.endswith("__") for name in names):
                continue
            result.append(n)
        elif isinstance(n, (ast.AugAssign,)):
            result.append(n)
    return result


def _const_name(node):
    """Get the name from an assignment node."""
    if isinstance(node, ast.Assign) and node.targets:
        t = node.targets[0]
        if isinstance(t, ast.Name):
            return t.id
    return ""


def _names_used(node):
    """All Name references within a node (the identifiers it touches)."""
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            # Capture the root of attribute access (e.g., 'os' in os.path)
            root = child
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name):
                names.add(root.id)
    return names


def _import_provided_names(imports):
    """Map each import node to the set of names it makes available."""
    result = {}
    for imp in imports:
        names = set()
        if isinstance(imp, ast.Import):
            for alias in imp.names:
                names.add(alias.asname or alias.name.split('.')[0])
        elif isinstance(imp, ast.ImportFrom):
            for alias in imp.names:
                names.add(alias.asname or alias.name)
            # Also add the module name root for `from X import Y` usage
        result[id(imp)] = names
    return result


def _filter_imports(imports, import_names, needed_names):
    """Keep only imports that provide names the function uses."""
    result = []
    for imp in imports:
        provided = import_names[id(imp)]
        if provided & needed_names:
            result.append(imp)
    return result


def _transitive_constants(constants, name_refs, needed_names):
    """Find constants that are needed, including constants referenced by other constants."""
    const_names = {_const_name(c) for c in constants}
    found = set()
    queue = list(needed_names & const_names)
    while queue:
        current = queue.pop()
        if current in found:
            continue
        found.add(current)
        # This constant may reference other constants
        refs = name_refs.get(current, set())
        for ref in refs:
            if ref in const_names and ref not in found:
                queue.append(ref)
    # Return in source order
    return [c for c in constants if _const_name(c) in found]


def _transitive_deps(fn_name, name_refs, priv_fns):
    """Find private helpers fn_name calls, transitively."""
    priv_names = {n.name for n in priv_fns}
    needed = set()
    queue = [fn_name]
    while queue:
        current = queue.pop()
        refs = name_refs.get(current, set())
        for ref in refs:
            if ref in priv_names and ref not in needed:
                needed.add(ref)
                queue.append(ref)
    # Return in source order
    return [n for n in priv_fns if n.name in needed]


def _node_source(node, lines):
    """Extract the source lines for an AST node, verbatim."""
    start = node.lineno - 1  # 0-indexed
    end = getattr(node, 'end_lineno', node.lineno)
    return ''.join(lines[start:end])


# --- SCRIPT_DIR pattern: os.path.dirname(os.path.abspath(__file__)) ---
_SCRIPT_DIR_RE = re.compile(
    r'(=\s*)os\.path\.dirname\(os\.path\.abspath\(__file__\)\)'
)


def _fix_script_dir_depth(const_src):
    """Wrap SCRIPT_DIR with extra os.path.dirname() for package depth."""
    return _SCRIPT_DIR_RE.sub(
        r'\1os.path.dirname(os.path.dirname(os.path.abspath(__file__)))',
        const_src,
    )


def _write_helpers_file(
    output_dir, shared_helper_nodes, name_refs, constants,
    imports, import_names, lines, module_doc, source_path, report,
):
    """Write _helpers.py containing private helpers used by 2+ public functions."""
    # Collect all names referenced by shared helpers (for imports + constants)
    all_ref_names = set()
    for node in shared_helper_nodes:
        all_ref_names |= name_refs.get(node.name, set())

    needed_constants = _transitive_constants(constants, name_refs, all_ref_names)
    for c in needed_constants:
        all_ref_names |= name_refs.get(_const_name(c), set())
    needed_imports = _filter_imports(imports, import_names, all_ref_names)

    out_lines = []
    if module_doc:
        first_line = module_doc.split('\n')[0]
        out_lines.append(f'# Shared helpers from: {os.path.basename(source_path)} — {first_line}\n')
    out_lines.append('\n')

    for imp_node in needed_imports:
        out_lines.append(_node_source(imp_node, lines))
    if needed_imports:
        out_lines.append('\n')

    for const_node in needed_constants:
        const_src = _node_source(const_node, lines)
        const_src = _fix_script_dir_depth(const_src)
        out_lines.append(const_src)
    if needed_constants:
        out_lines.append('\n')

    for node in shared_helper_nodes:
        out_lines.append('\n')
        out_lines.append(_node_source(node, lines))

    out_path = os.path.join(output_dir, '_helpers.py')
    with open(out_path, 'w') as f:
        content = ''.join(out_lines)
        while '\n\n\n\n' in content:
            content = content.replace('\n\n\n\n', '\n\n\n')
        f.write(content)
    print("  _helpers.py")


class _StubReport:
    """Collects auto-fix actions for the post-stub report."""

    def __init__(self):
        self.cross_imports = []       # (consumer, sibling)
        self.shared_helper_names = []  # helper names in _helpers.py
        self.script_dir_fixes = []     # filenames where SCRIPT_DIR was adjusted
        self.subprocess_refs = []      # filenames with subprocess calls to original

    def print_report(self, num_files, output_dir, basename):
        print(f"\nStubbed {num_files} functions into {output_dir}/")

        if self.cross_imports:
            print(f"\n  Auto cross-imports ({len(self.cross_imports)}):")
            for consumer, sibling in self.cross_imports:
                print(f"    {consumer}.py ← from .{sibling} import {sibling}")

        if self.shared_helper_names:
            print(f"\n  Shared helpers → _helpers.py ({len(self.shared_helper_names)}):")
            for name in self.shared_helper_names:
                print(f"    {name}")

        if self.script_dir_fixes:
            unique = sorted(set(self.script_dir_fixes))
            print(f"\n  SCRIPT_DIR depth adjusted ({len(unique)} files):")
            for fname in unique:
                print(f"    {fname}.py")

        if self.subprocess_refs:
            unique = sorted(set(self.subprocess_refs))
            print(f"\n  Subprocess calls referencing '{basename}' (need -m update):")
            for fname in unique:
                print(f"    {fname}.py")

        # Consumer import checklist
        print(f"\n  Remaining manual steps:")
        print(f"    1. Update external consumers: `import {basename}` → `from {basename} import func`")
        print(f"    2. Update subprocess calls: `python3 {basename}.py` → `python3 -m {basename}`")
        print(f"    3. Remove original: `{basename}.py`")
