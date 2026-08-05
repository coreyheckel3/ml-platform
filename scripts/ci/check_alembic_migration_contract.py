from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VERSIONS_DIR = Path("backend/alembic/versions")
DEFAULT_OUTPUT_PATH = Path("contracts/database/alembic-migrations.v1.json")
MIGRATION_CONTRACT_SCHEMA_VERSION = "forgeml.alembic_migrations.v1"


@dataclass(frozen=True)
class MigrationRevision:
    revision: str
    down_revisions: tuple[str, ...]
    path: Path
    has_upgrade: bool
    has_downgrade: bool


def extract_migration_revisions(
    versions_dir: Path = DEFAULT_VERSIONS_DIR,
) -> tuple[MigrationRevision, ...]:
    if not versions_dir.is_dir():
        return ()

    revisions = [
        _extract_migration_revision(path)
        for path in sorted(versions_dir.glob("*.py"), key=lambda candidate: candidate.name)
    ]
    return tuple(sorted(revisions, key=lambda revision: (revision.revision, revision.path.name)))


def build_migration_contract(
    versions_dir: Path = DEFAULT_VERSIONS_DIR,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    migrations = extract_migration_revisions(versions_dir)
    bases = _find_bases(migrations)
    heads = _find_heads(migrations)
    children_by_revision = _children_by_revision(migrations)
    linearized_order = _linearized_revision_order(migrations, bases, children_by_revision)
    branch_points = sorted(
        revision
        for revision, children in children_by_revision.items()
        if revision and len(children) > 1
    )
    merge_revisions = sorted(
        migration.revision for migration in migrations if len(migration.down_revisions) > 1
    )

    return {
        "schema_version": MIGRATION_CONTRACT_SCHEMA_VERSION,
        "generated_from": [_display_path(versions_dir, repo_root)],
        "summary": {
            "migration_count": len(migrations),
            "base_revision": bases[0] if len(bases) == 1 else None,
            "head_revision": heads[0] if len(heads) == 1 else None,
            "base_count": len(bases),
            "head_count": len(heads),
            "branch_point_count": len(branch_points),
            "merge_revision_count": len(merge_revisions),
        },
        "bases": bases,
        "heads": heads,
        "branch_points": branch_points,
        "merge_revisions": merge_revisions,
        "linearized_revision_order": linearized_order,
        "migrations": [
            {
                "revision": migration.revision,
                "down_revisions": list(migration.down_revisions),
                "path": _display_path(migration.path, repo_root),
                "has_upgrade": migration.has_upgrade,
                "has_downgrade": migration.has_downgrade,
            }
            for migration in migrations
        ],
    }


def validate_migration_graph(migrations: tuple[MigrationRevision, ...]) -> tuple[str, ...]:
    findings: list[str] = []
    if not migrations:
        return ("No Alembic migration files were found.",)

    revisions_by_id: dict[str, MigrationRevision] = {}
    duplicate_revisions: set[str] = set()
    for migration in migrations:
        if not migration.revision:
            findings.append(f"{migration.path} does not declare a revision.")
            continue
        if migration.revision in revisions_by_id:
            duplicate_revisions.add(migration.revision)
        revisions_by_id[migration.revision] = migration
        if not migration.has_upgrade:
            findings.append(f"{migration.revision} does not define upgrade().")
        if not migration.has_downgrade:
            findings.append(f"{migration.revision} does not define downgrade().")

    for revision in sorted(duplicate_revisions):
        findings.append(f"Duplicate Alembic revision: {revision}.")

    known_revisions = set(revisions_by_id)
    for migration in migrations:
        for down_revision in migration.down_revisions:
            if down_revision not in known_revisions:
                findings.append(
                    f"{migration.revision} references unknown down_revision {down_revision}."
                )

    bases = _find_bases(migrations)
    heads = _find_heads(migrations)
    if len(bases) != 1:
        findings.append(f"Expected exactly one Alembic base revision, found {len(bases)}.")
    if len(heads) != 1:
        findings.append(f"Expected exactly one Alembic head revision, found {len(heads)}.")

    children_by_revision = _children_by_revision(migrations)
    reachable = _reachable_revisions(bases, children_by_revision)
    unreachable = sorted(known_revisions - reachable)
    if unreachable:
        findings.append(f"Unreachable Alembic revisions: {', '.join(unreachable)}.")

    cycle = _find_cycle(bases, children_by_revision)
    if cycle:
        findings.append(f"Alembic revision cycle detected: {' -> '.join(cycle)}.")

    return tuple(findings)


def serialize_migration_contract(contract: dict[str, Any]) -> str:
    return json.dumps(contract, indent=2, sort_keys=True) + "\n"


def write_migration_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    versions_dir: Path = DEFAULT_VERSIONS_DIR,
    repo_root: Path = REPO_ROOT,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        serialize_migration_contract(build_migration_contract(versions_dir, repo_root)),
        encoding="utf-8",
    )


def check_migration_contract(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    versions_dir: Path = DEFAULT_VERSIONS_DIR,
    repo_root: Path = REPO_ROOT,
) -> tuple[bool, str]:
    migrations = extract_migration_revisions(versions_dir)
    findings = validate_migration_graph(migrations)
    if findings:
        return False, "Alembic migration contract violations: " + "; ".join(findings)

    if not output_path.is_file():
        return False, f"Alembic migration contract does not exist: {output_path}"

    expected = serialize_migration_contract(build_migration_contract(versions_dir, repo_root))
    actual = output_path.read_text(encoding="utf-8")
    if actual != expected:
        return False, f"Alembic migration contract is stale: {output_path}"
    head = build_migration_contract(versions_dir, repo_root)["summary"]["head_revision"]
    return True, f"Alembic migration contract is current at head {head}: {output_path}"


def _extract_migration_revision(path: Path) -> MigrationRevision:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    metadata = _extract_module_metadata(tree)
    functions = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    return MigrationRevision(
        revision=str(metadata.get("revision") or ""),
        down_revisions=_normalize_down_revisions(metadata.get("down_revision")),
        path=path,
        has_upgrade="upgrade" in functions,
        has_downgrade="downgrade" in functions,
    )


def _extract_module_metadata(tree: ast.Module) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for node in tree.body:
        target_name: str | None = None
        value_node: ast.expr | None = None
        if isinstance(node, ast.Assign):
            target_name = _single_assignment_target(node.targets)
            value_node = node.value
        elif isinstance(node, ast.AnnAssign):
            target_name = node.target.id if isinstance(node.target, ast.Name) else None
            value_node = node.value

        if target_name in {"revision", "down_revision"} and value_node is not None:
            metadata[target_name] = _literal_value(value_node)
    return metadata


def _single_assignment_target(targets: list[ast.expr]) -> str | None:
    if len(targets) != 1:
        return None
    target = targets[0]
    return target.id if isinstance(target, ast.Name) else None


def _literal_value(node: ast.expr) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Tuple | ast.List | ast.Set):
        return tuple(_literal_value(element) for element in node.elts)
    return None


def _normalize_down_revisions(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, tuple | list | set):
        return tuple(sorted(str(item) for item in value if item is not None))
    return ()


def _find_bases(migrations: tuple[MigrationRevision, ...]) -> list[str]:
    return sorted(migration.revision for migration in migrations if not migration.down_revisions)


def _find_heads(migrations: tuple[MigrationRevision, ...]) -> list[str]:
    revisions = {migration.revision for migration in migrations if migration.revision}
    referenced_revisions = {
        down_revision for migration in migrations for down_revision in migration.down_revisions
    }
    return sorted(revisions - referenced_revisions)


def _children_by_revision(
    migrations: tuple[MigrationRevision, ...],
) -> dict[str, tuple[str, ...]]:
    children: dict[str, list[str]] = defaultdict(list)
    for migration in migrations:
        for down_revision in migration.down_revisions:
            children[down_revision].append(migration.revision)
    return {
        revision: tuple(sorted(revision_children))
        for revision, revision_children in children.items()
    }


def _reachable_revisions(
    bases: list[str],
    children_by_revision: dict[str, tuple[str, ...]],
) -> set[str]:
    reachable: set[str] = set()
    stack = list(bases)
    while stack:
        revision = stack.pop()
        if revision in reachable:
            continue
        reachable.add(revision)
        stack.extend(children_by_revision.get(revision, ()))
    return reachable


def _find_cycle(
    bases: list[str],
    children_by_revision: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(revision: str, path: tuple[str, ...]) -> tuple[str, ...]:
        if revision in visiting:
            start_index = path.index(revision) if revision in path else 0
            return (*path[start_index:], revision)
        if revision in visited:
            return ()
        visiting.add(revision)
        for child_revision in children_by_revision.get(revision, ()):
            cycle = visit(child_revision, (*path, revision))
            if cycle:
                return cycle
        visiting.remove(revision)
        visited.add(revision)
        return ()

    for base_revision in bases:
        cycle = visit(base_revision, ())
        if cycle:
            return cycle
    return ()


def _linearized_revision_order(
    migrations: tuple[MigrationRevision, ...],
    bases: list[str],
    children_by_revision: dict[str, tuple[str, ...]],
) -> list[str]:
    if not bases:
        return []

    ordered: list[str] = []
    seen: set[str] = set()

    def visit(revision: str) -> None:
        if revision in seen:
            return
        seen.add(revision)
        ordered.append(revision)
        for child_revision in children_by_revision.get(revision, ()):
            visit(child_revision)

    for base_revision in bases:
        visit(base_revision)

    known_revisions = {migration.revision for migration in migrations}
    ordered.extend(sorted(known_revisions - set(ordered)))
    return ordered


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify ForgeML Alembic migration topology.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the checked-in Alembic migration contract.",
    )
    parser.add_argument(
        "--versions-dir",
        type=Path,
        default=DEFAULT_VERSIONS_DIR,
        help="Path to Alembic migration version files.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Regenerate the checked-in Alembic migration contract.",
    )
    args = parser.parse_args(argv)

    if args.write:
        write_migration_contract(args.output, args.versions_dir)
        print(f"Wrote Alembic migration contract: {args.output}")
        return 0

    passed, detail = check_migration_contract(args.output, args.versions_dir)
    print(("PASS " if passed else "FAIL ") + detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
