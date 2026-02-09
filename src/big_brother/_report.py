"""How big brother communicates — laws first, then the verdict."""  # bb:vetted

from big_brother._laws import LAWS


def print_laws(args):
    """State the law before enforcing it — no secret rules."""
    print("Laws:")
    for i, law in enumerate(LAWS, 1):
        print(f"  {i}. {law}")
    # LOC limits are configurable, so print the active values.
    print(f"  {len(LAWS) + 1}. Source files ≤{args.source_max} LOC, test files ≤{args.test_max} LOC")
    print()


def print_report(violations, vetted, lines=False):
    """Two sections: unvetted (actionable) and vetted (acknowledged).
    Everything is visible — nothing hides. --strict only counts unvetted."""
    if not violations and not vetted:
        print("No violations found.")
        return

    # Unvetted — the gatekeeper hasn't reviewed these yet.
    if violations:
        by_rule = {}
        for v in violations:
            rule, detail = v[0], v[1]
            fn_lines = v[2] if len(v) > 2 else None
            by_rule.setdefault(rule, []).append((detail, fn_lines))

        print(f"\n{'Rule':<12}  {'Count':>5}  Detail")
        print("-" * 80)
        for rule, entries in sorted(by_rule.items()):
            for i, (detail, fn_lines) in enumerate(entries):
                label = rule if i == 0 else ""
                count = str(len(entries)) if i == 0 else ""
                print(f"{label:<12}  {count:>5}  {detail}")
                if lines and fn_lines:
                    for name, start, end in fn_lines:
                        print(f"{'':>20}  {name:<30s} L{start}-L{end}")
        print(f"\n{len(violations)} violation(s)")
        print("To vet: add '# bb:vetted' to the first 10 lines of the file.")

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
