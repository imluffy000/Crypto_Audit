"""Input filters: size limits and directories excluded from scans."""



MAX_SOURCE_BYTES = 1_000_000


EXCLUDED_DIRS = frozenset({".git", ".venv", "venv", "env", "node_modules", "__pycache__", "build", "dist", ".tox", ".mypy_cache"})
