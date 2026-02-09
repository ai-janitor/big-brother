"""How big brother communicates — laws first, then the verdict."""  # bb:vetted

from big_brother._laws import LAWS, COHESION_CRITERIA, PRINCIPLES


def print_laws(args):
    """State the law before enforcing it — no secret rules."""
    print("Laws:")
    for i, law in enumerate(LAWS, 1):
        print(f"  {i}. {law}")
    # LOC limits are configurable, so print the active values.
    print(f"  {len(LAWS) + 1}. Source files ≤{args.source_max} LOC, test files ≤{args.test_max} LOC")
    print()
    print('  "Logic" = any top-level def, async def, or class whose name')
    print("  doesn't start with underscore. Private helpers (_foo) don't count.")
    print()
    print("Principles:")
    for p in PRINCIPLES:
        print(f"  - {p}")
    print()


def print_report(violations, vetted, lines=False):
    """Two sections: unvetted (actionable) and vetted (acknowledged).
    Everything is visible — nothing hides. --strict only counts unvetted."""
    if not violations and not vetted:
        print("No violations found.")
        return

    # Unvetted — the gatekeeper hasn't reviewed these yet.
    if violations:
        print(f"\nViolations ({len(violations)}):\n")
        for v in violations:
            rule, detail = v[0], v[1]
            fn_lines = v[2] if len(v) > 2 else None
            print(f"  {detail}")
            if lines and fn_lines:
                for name, start, end in fn_lines:
                    print(f"    {name}  L{start}-L{end}")
        print(f"\nTo vet: add '# bb:vetted' to the first 10 lines of the file.")
        print("Vet when:")
        for c in COHESION_CRITERIA:
            print(f"  - {c}")

    # Vetted — gatekeeper reviewed, cohesion judgment applied.
    # Still visible so nothing hides, but won't block CI.
    if vetted:
        print(f"\n--- vetted ({len(vetted)}) ---")
        for v in vetted:
            detail = v[1]
            fn_lines = v[2] if len(v) > 2 else None
            print(f"  {detail}")
            if lines and fn_lines:
                for name, start, end in fn_lines:
                    print(f"{'':>4}  {name:<30s} L{start}-L{end}")

    if not violations:
        print("No unvetted violations.")
