"""Import diagnostics for MCP server startup and CI validation."""

from __future__ import annotations

import ast
import importlib
import importlib.util
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "mynat_ai_system"
INTERNAL_PACKAGES = {
    "agent_memory_system",
    "agents",
    "ai_cost_tracking",
    "backend",
    "campaign_pattern_learner_engine",
    "database",
    "mcp_server",
    "monitoring",
    "webhooks",
    "workflows",
}
CRITICAL_IMPORTS = (
    "mcp_server.tool_registry",
    "mcp_server.tools.website_scraper_tool",
    "mcp_server.tools.seo_analysis_tool",
    "mcp_server.tools.product_rec_tool",
    "mcp_server.bridges",
    "agents.campaign_creator.creator_agent",
    "agents.caption_writer.agent",
    "agents.content_verifier.agent",
    "backend.database.db_connection",
    "backend.automation.task_scheduler",
    "campaign_pattern_learner_engine.campaign_pattern_learner",
    "agent_memory_system.memory_service",
    "webhooks.webhook_api",
)


def _python_files() -> list[Path]:
    return sorted(
        path
        for path in APP_ROOT.rglob("*.py")
        if "archive" not in path.parts and "__pycache__" not in path.parts
    )


def _module_name(path: Path) -> str:
    rel = path.relative_to(APP_ROOT).with_suffix("")
    parts = rel.parts[:-1] if rel.name == "__init__" else rel.parts
    return ".".join(parts)


def _iter_imports(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                imports.append("." * node.level + (node.module or ""))
            elif node.module:
                imports.append(node.module)
    return imports


def _normalize_internal_import(imported: str) -> str:
    if imported.startswith("."):
        return imported
    if imported.startswith("mynat_ai_system."):
        parts = imported.split(".")
        if len(parts) >= 2 and parts[1] in INTERNAL_PACKAGES:
            return ".".join(parts[1:])
    return imported


def report_import_graph() -> dict[str, list[str]]:
    """Return internal import edges without importing application modules."""
    graph: dict[str, list[str]] = {}
    for path in _python_files():
        module = _module_name(path)
        edges = []
        for imported in _iter_imports(path):
            imported = _normalize_internal_import(imported)
            root = imported.split(".", 1)[0].lstrip(".")
            if root in INTERNAL_PACKAGES:
                edges.append(imported)
        graph[module] = sorted(set(edges))
    return graph


def detect_circular_imports() -> list[list[str]]:
    """Detect cycles in the static internal import graph."""
    graph = report_import_graph()
    normalized: dict[str, set[str]] = {}
    for module, imports in graph.items():
        package_edges = set()
        for imported in imports:
            if imported.startswith("."):
                continue
            parts = imported.split(".")
            for idx in range(len(parts), 0, -1):
                candidate = ".".join(parts[:idx])
                if candidate in graph:
                    package_edges.add(candidate)
                    break
        normalized[module] = package_edges

    cycles: list[list[str]] = []
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(module: str) -> None:
        if module in visiting:
            cycle = visiting[visiting.index(module) :] + [module]
            if cycle not in cycles:
                cycles.append(cycle)
            return
        if module in visited:
            return
        visiting.append(module)
        for dependency in normalized.get(module, set()):
            visit(dependency)
        visiting.pop()
        visited.add(module)

    for module in normalized:
        visit(module)
    return cycles


def detect_missing_modules() -> list[dict[str, str]]:
    """Import critical modules and return any startup failures."""
    failures: list[dict[str, str]] = []
    for module in CRITICAL_IMPORTS:
        try:
            if importlib.util.find_spec(module) is None:
                failures.append({"module": module, "error": "module spec not found"})
                continue
            importlib.import_module(module)
        except Exception as exc:  # noqa: BLE001 - diagnostics must report every failure.
            failures.append({"module": module, "error": f"{type(exc).__name__}: {exc}"})
    return failures


def validate_packages() -> dict[str, Any]:
    """Validate package markers and cwd-independent compatibility packages."""
    missing_init = []
    for directory in sorted(path for path in APP_ROOT.rglob("*") if path.is_dir()):
        if "archive" in directory.parts or "__pycache__" in directory.parts:
            continue
        if any(child.suffix == ".py" for child in directory.iterdir() if child.is_file()):
            init_file = directory / "__init__.py"
            if not init_file.exists():
                missing_init.append(str(directory.relative_to(PROJECT_ROOT)))

    missing_compat = []
    for package in sorted(INTERNAL_PACKAGES):
        if importlib.util.find_spec(package) is None:
            missing_compat.append(package)

    return {"missing_init_files": missing_init, "missing_compat_packages": missing_compat}


def check_imports() -> dict[str, Any]:
    """Run all import diagnostics and return a machine-readable report."""
    package_report = validate_packages()
    missing_modules = detect_missing_modules()
    circular_imports = detect_circular_imports()
    relative_imports = {
        str(path.relative_to(PROJECT_ROOT)): [
            imported for imported in _iter_imports(path) if imported.startswith(".")
        ]
        for path in _python_files()
    }
    relative_imports = {path: imports for path, imports in relative_imports.items() if imports}

    ok = not (
        package_report["missing_init_files"]
        or package_report["missing_compat_packages"]
        or missing_modules
        or relative_imports
    )
    return {
        "success": ok,
        "packages": package_report,
        "missing_modules": missing_modules,
        "circular_imports": circular_imports,
        "relative_imports": relative_imports,
        "import_graph": report_import_graph(),
    }
