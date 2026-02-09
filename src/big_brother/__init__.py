"""Pattern enforcer — scan a Python project for structural violations.

This codebase is AI-first. It is organized for agents that `ls` a directory
and know what every file does by its name — not for humans clicking through
an IDE. If the filenames look verbose to you, you are not the audience.

Big brother sees everything but judges nothing. It reports every violation
it finds — the agent (gatekeeper) decides which are acceptable cohesion
and which are real debt. Files the gatekeeper has reviewed get marked
with `# bb:vetted` and move to the acknowledged section.

Philosophy:
  The law is the default: 1 file, 1 function. Laws exist because agents
  get dumb past ~800 LOC and can't find functions buried in large files.
  But cohesion is real — some functions are meaningless alone. The gatekeeper
  applies that judgment. Big brother just enforces visibility.

Usage:
    python3 -m big_brother .                    # scan current dir
    python3 -m big_brother . --strict           # exit 1 on unvetted violations only
    python3 -m big_brother . --ignore "test_*"  # skip patterns
"""

import argparse
import os
import sys

from big_brother._scanner import scan
from big_brother._report import print_laws, print_report

__version__ = "0.1.0"
__all__ = ["main", "scan", "print_report", "print_laws", "stub"]


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""\
big-brother — AI-first Python code structure enforcer.

Scan: walks every .py file under a directory, runs 4 checks, reports
violations. Files with '# bb:vetted' in the first 10 lines still show
in output but are separated into the "vetted" section and don't block
--strict.

Checks (run on every .py file):
  1. multi-def  — >1 public def per file (the core law)
     "Logic" = any top-level def, async def, or class whose name
     doesn't start with underscore. Private helpers (_foo) don't count.
  2. loc        — source files >800 LOC, test files >500 LOC
     (limits configurable via --source-max, --test-max)
  3. missing-all — __init__.py has re-exports but no __all__
  4. entry      — entry files (main.*, app.*, server.*, run.*, start.*,
     index.*, entry.*, bootstrap.*, __main__.py, setup.py) with >3
     non-main defs

Skips: .git, __pycache__, .venv, venv, node_modules, .tox, .mypy_cache
  __init__.py gets checks 2+3 only (multi-def expected in init files).
  Test files (path contains 'test') get check 2 only.

Output: two sections — Violations (unvetted, actionable) and Vetted
  (acknowledged, won't block CI). Everything is visible, nothing hides.
  --lines adds L{start}-L{end} ranges per def in each violation.
  --strict exits 1 only on unvetted violations (for CI gates).

bb:vetted — gatekeeper judgment:
  Add '# bb:vetted' anywhere in the first 10 lines of a file.
  This is a human/agent judgment call: the file has multiple public
  defs but they are cohesive (always modified together, meaningless
  apart, file under ~300 LOC). Vetted files move to the acknowledged
  section. They still appear in output so nothing hides.

Workflow:
  big-brother .                        Scan and see violations
  big-brother . --lines                Show line ranges per def
  big-brother . --strict               CI gate — exit 1 on unvetted only
  big-brother --stub bloated.py        Decompose monolith into package
  big-brother --stub bloated.py --output pkg/   Custom output dir

--stub: Monolith decomposer
  Reads a .py file with 2+ public defs, writes a 1-file-1-def package.
  Each public function, async function, or class gets its own file.
  What it does automatically:
    - AST-traces each def's dependencies (imports, constants, private helpers)
    - Each output file gets only the imports/constants it actually uses
    - Private helpers used by 2+ defs → shared _helpers.py (no duplication)
    - Private helpers used by 1 def → colocated in that def's file
    - Cross-imports between sibling defs → relative imports added
    - SCRIPT_DIR depth adjusted for package nesting
    - __init__.py with __all__ and re-exports
    - __main__.py if a main() function exists
  What you still do manually:
    - Update external consumers to import from the new package
    - Update subprocess calls (python3 file.py → python3 -m pkg)
    - Delete the original monolith

Principles:
  - Design your files well — exceptions only for cohesiveness, and even then rare
  - Folder paths give you free relationships — exploit that for organization
  - Comments convey meaning — meaning is much less fragile than code
  - Descriptive filenames over short ones — long_descriptive_name.py is fine
  - This is not for you, point-and-click IDE humans — this is for agents""",
    )
    parser.add_argument("path", nargs="?", default=".", help="Root directory to scan")
    parser.add_argument("--strict", action="store_true", help="CI gate — exit 1 on unvetted violations only")
    parser.add_argument("--ignore", action="append", default=[], help="Glob patterns to skip (e.g. 'test_*')")
    parser.add_argument("--source-max", type=int, default=800, help="Max LOC for source files (default: 800)")
    parser.add_argument("--test-max", type=int, default=500, help="Max LOC for test files (default: 500)")
    parser.add_argument("--lines", action="store_true", help="Show line ranges for each function/class")
    parser.add_argument("--stub", metavar="FILE", help="Decompose a multi-def file into a 1-file-1-def package (see above)")
    parser.add_argument("--output", metavar="DIR", help="Output dir for --stub (default: <file>/ in same dir)")
    args = parser.parse_args()

    if args.stub:
        from big_brother._stub import stub
        stub(args.stub, args.output)
        return

    root = os.path.abspath(args.path)
    print_laws(args)

    violations, vetted = scan(root, args)
    print_report(violations, vetted, lines=args.lines)

    if args.strict and violations:
        sys.exit(1)
