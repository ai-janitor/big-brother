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
    "One unit of logic per .py file (function or class)",
    "Cohesive small modules may stay together — vet with '# bb:vetted'",
    "__init__.py with re-exports must have __all__",
    "Entry files ≤3 non-main defs",
]

# When to vet: guidance for AI gatekeepers deciding cohesion.
COHESION_CRITERIA = [
    "Functions are always modified together",
    "Functions are meaningless apart",
    "File is under ~300 LOC",
]

# Principles — how to organize, not just what to flag.
# Printed so any AI agent reading bb output knows the philosophy.
PRINCIPLES = [
    "Design your files well — exceptions only for cohesiveness, and even then rare",
    "Folder paths give you free relationships — exploit that for organization",
    "Comments convey meaning — meaning is much less fragile than code",
    "Descriptive filenames over short ones — long_descriptive_name.py is fine",
    "This is not for you, point-and-click IDE humans — this is for agents",
]
