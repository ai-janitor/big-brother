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
    parser = argparse.ArgumentParser(description="Scan Python project for structural violations")
    parser.add_argument("path", nargs="?", default=".", help="Root directory to scan")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on unvetted violations")
    parser.add_argument("--ignore", action="append", default=[], help="Glob patterns to skip")
    parser.add_argument("--source-max", type=int, default=800, help="Source file LOC limit")
    parser.add_argument("--test-max", type=int, default=500, help="Test file LOC limit")
    parser.add_argument("--lines", action="store_true", help="Show line ranges for each function")
    parser.add_argument("--stub", metavar="FILE", help="Extract public functions into a package")
    parser.add_argument("--output", metavar="DIR", help="Output directory for --stub (default: <file>/ in same dir)")
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
