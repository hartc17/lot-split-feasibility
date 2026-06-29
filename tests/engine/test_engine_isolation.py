"""Verify the engine module imports no DB, adapter, or I/O modules."""

import ast
from pathlib import Path


def _get_imports(filepath: Path) -> list[str]:
    tree = ast.parse(filepath.read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def test_engine_has_no_db_imports():
    engine_dir = Path("app/engine")
    forbidden = {"app.models", "app.adapters", "sqlalchemy", "geoalchemy2", "psycopg2"}
    violations = []
    for py_file in engine_dir.rglob("*.py"):
        for imp in _get_imports(py_file):
            if any(imp.startswith(f) for f in forbidden):
                violations.append(f"{py_file}: imports {imp!r}")
    assert violations == [], "\n".join(violations)
