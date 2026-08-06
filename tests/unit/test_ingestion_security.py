from __future__ import annotations

import ast
from pathlib import Path


def test_ingestion_module_has_no_dynamic_execution_paths() -> None:
    source = Path("apps/api/app/ingestion.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden_imports = {"subprocess", "importlib"}
    forbidden_calls = {"eval", "exec", "__import__", "compile"}
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_name = alias.name.split(".", maxsplit=1)[0]
                if root_name in forbidden_imports:
                    violations.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root_name = (node.module or "").split(".", maxsplit=1)[0]
            if root_name in forbidden_imports:
                violations.append(f"from {node.module} import ...")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in forbidden_calls:
                violations.append(f"call {node.func.id}")
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "system"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
            ):
                violations.append("call os.system")
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in forbidden_imports
            ):
                violations.append(f"call {node.func.value.id}.{node.func.attr}")

    assert violations == []
