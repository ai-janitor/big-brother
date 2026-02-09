# big-brother

AI-first Python code structure enforcer — **1 file, 1 function.**

Code is organized for agents that `ls` a directory and know what every file does by its name. Big brother sees everything but judges nothing — it reports violations, the gatekeeper decides which are acceptable cohesion and which are real debt.

## Install

```bash
pip install py-big-brother
```

## CLI Usage

```bash
# Scan a project
big-brother .

# Exit 1 on unvetted violations (for CI)
big-brother . --strict

# Skip patterns
big-brother . --ignore "test_*" --ignore "migrations/*"

# Show line ranges per function
big-brother . --lines

# Custom LOC limits
big-brother . --source-max 600 --test-max 400

# Extract a monolith into a 1-file-1-function package
big-brother --stub server.py --output server/
```

Module invocation also works:

```bash
python3 -m big_brother .
```

## Python API

```python
from big_brother import scan, print_report, print_laws

# scan() needs an args-like object with: ignore, source_max, test_max
import argparse
args = argparse.Namespace(ignore=[], source_max=800, test_max=500)

violations, vetted = scan("/path/to/project", args)
print_report(violations, vetted, lines=False)
```

## The Laws

1. **One public function per `.py` file** — filenames ARE the API
2. **`__init__.py` with re-exports must have `__all__`** — no opaque packages
3. **Entry files ≤3 non-main defs** — routers route, they don't work
4. **Source files ≤800 LOC, test files ≤500 LOC** — agents lose coherence past these limits

## Vetting

Not every violation needs fixing. Cohesive small functions that are always modified together can stay in one file. To acknowledge a reviewed file:

Add `# bb:vetted` to the first 10 lines of the file (usually in the module docstring). Vetted files still appear in output but won't block `--strict`.

## License

MIT
