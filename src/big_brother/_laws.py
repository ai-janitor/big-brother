"""What big brother watches for — the laws and where to look."""

# Files named like these are entry points — routers, not libraries.
# They get a separate check: too many defs means the entry file
# is doing work that belongs in importable modules.
ENTRY_PATTERNS = [
    "main.*", "index.*", "app.*", "server.*",
    "run.*", "start.*", "entry.*", "bootstrap.*",
    "__main__.py", "setup.py",
]

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".tox", ".mypy_cache"}

# Printed at the top of every scan so the subject knows what
# they're being measured against. No secret rules.
LAWS = [
    "One public function per .py file",
    "__init__.py with re-exports must have __all__",
    "Entry files ≤3 non-main defs",
]
