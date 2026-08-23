"""Permanent repository architecture invariants (fresh-start)."""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
_TOOLS = _ROOT / "tools"
_INV = _TOOLS / "investigation"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain import paths as domain_paths  # noqa: E402
from domain.paths import characters_data_dir, holy_grail_data_dir, sessions_data_dir  # noqa: E402
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402

_AUTOGEN_IMPORT_ROOTS = frozenset(
    {"autogen", "autogen_agentchat", "autogen_core", "autogen_ext", "autogenstudio", "pyautogen"}
)
_PRODUCTION_FORBIDDEN_TOKENS = (
    "legacy.v1_orchestration",
    "v1_orchestration",
    "turn_runner",
    "model_client",
    "python.rp_app",
    "rp_app",
)

_GOVERNANCE_CORPUS_FILES = (
    "workflow-weights.md",
    "issue-tracking-workflow.md",
    "audit-semantics.md",
    "project-behavior-holy-grail.md",
    "holy-grail-prd.md",
    "architecture-overview.md",
)

_REMOVED_GPT_WORKFLOW_REPO_PATH = "governance/sources/gpt-workflow-instruction-set.md"

_CONTRACT_AUTHORITY_DOCS = (
    _ROOT / "GLOSSARY.md",
    _ROOT / "PACKET_CONTRACTS.md",
    _ROOT / "CANONICAL_KNOWLEDGE_MODEL.md",
    _ROOT / "AUTHORED_SOURCE_CONTRACT.md",
)

_DELETED_ROOT_DOC_PATHS = (
    "failure_taxomony_spec_v1.md",
    "memory_packet_contract_v1.md",
    "Token efficiency plan.md",
    "runtime_narrative_memory_prd1.md",
    "narrative_knowledge_ingestion_prd2.md",
    "roadmap.md",
    "REGISTRY_VALIDATION_REPORT.md",
    "data/retrieval/OPERATIONAL_RETRIEVAL_PILOT.md",
)

_CURRENT_NAVIGATION_DOCS = (
    _ROOT / "AGENTS.md",
    _ROOT / "governance" / "sources" / "architecture-overview.md",
    _ROOT / "MODULE_INDEX.md",
    _ROOT / "DEBUGGING_GUIDE.md",
    _ROOT / "docs" / "architecture.md",
    _ROOT / "docs" / "repo-map.md",
    _ROOT / "docs" / "rp-data-layout.md",
    _ROOT / "docs" / "core-operating-invariants.md",
    _ROOT / "v2" / "README.md",
)

_RETIRED_TURN_LOOP_LANDINGS = (
    "app_turn_director.py",
    "turn_runner.py",
    "orchestration_helpers.py",
    "app_turn_prompting.py",
    "model_client.py",
    "llm_client.py",
    "headless_scene_simulation.py",
    "bootstrap_composition.py",
    "ui_chat.py",
    "session_lifecycle_save.py",
    "session_lifecycle_load.py",
    "context_builder.py",
    "memory_store.py",
    "prompt_store.py",
    "python/rp_app/",
    "autogen_rp/",
)

_LIVE_RESPONSIBILITY_ROOTS = (
    "v2/domain",
    "v2/domain_api",
    "v2/rp_runtime",
    "v2/ui",
)

_AUDIT_SEMANTICS_PATH = _ROOT / "governance" / "sources" / "audit-semantics.md"
_AUDIT_PROCEDURE_PATH = _ROOT / "docs" / "audit-workflows.md"
_AUDIT_AUTHORITY_NAV_SURFACES = (
    _ROOT / "AGENTS.md",
    _ROOT / "docs" / "rp-data-layout.md",
    _ROOT / "docs" / "core-operating-invariants.md",
    _ROOT / "SCENARIO_VALIDATION_FRAMEWORK.md",
    _AUDIT_PROCEDURE_PATH,
)
_GOVERNANCE_README_PATH = _ROOT / "governance" / "README.md"
_GOVERNANCE_SOURCES_DIR = _ROOT / "governance" / "sources"
_GOVERNANCE_EXECUTION_DIR = _ROOT / "governance" / "execution"
_GOVERNANCE_RECORDS_DIR = _ROOT / "governance" / "records"
_ISSUE9_RELOCATED_RECORDS = (
    _GOVERNANCE_RECORDS_DIR / "runtime-narrative-memory-prd1.md",
    _GOVERNANCE_RECORDS_DIR / "narrative-knowledge-ingestion-prd2.md",
    _GOVERNANCE_RECORDS_DIR / "registry-validation-report.md",
    _GOVERNANCE_RECORDS_DIR / "token-efficiency-plan-issue-145.md",
    _GOVERNANCE_RECORDS_DIR / "operational-retrieval-pilot.md",
    _GOVERNANCE_RECORDS_DIR / "progression-layer-validation-status-v1.md",
)
_RETIRED_GOVERNANCE_PATH_PREFIXES = (
    "governance/policies/",
    "governance/rp-app/",
    "governance/github/",
)
_CURRENT_AUTHORITY_SURFACES = (
    _ROOT / "AGENTS.md",
    _ROOT / "docs" / "issue-bootstrap-profiles.md",
    _ROOT / "bindings" / "bindings.toml",
    _ROOT / "governance" / "project-sync.toml",
    _ROOT / "governance" / "README.md",
    _ROOT / "docs" / "repo-map.md",
    _ROOT / ".github" / "ISSUE_TEMPLATE" / "holy_grail_rp.yml",
)
_HISTORICAL_WORKSHOP_PATHS = (
    _ROOT / "governance" / "records" / "audit-classification-protocol.md",
    _ROOT / "governance" / "records" / "failure-taxonomy-spec-v1.md",
    _ROOT / "governance" / "records" / "round-a-strata-grid-v0.md",
    _ROOT / "governance" / "records" / "round-a-serialized-exemplar-export-checklist-v0.md",
)


def _iter_python_files(*roots: Path) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if any(part in {".venv", ".pytest_cache", "governance"} for part in path.parts):
                continue
            out.append(path)
    return out


def _autogen_import_offenders(paths: list[Path]) -> list[str]:
    offenders: list[str] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in _AUTOGEN_IMPORT_ROOTS:
                        offenders.append(f"{path.relative_to(_ROOT)}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root in _AUTOGEN_IMPORT_ROOTS:
                    offenders.append(f"{path.relative_to(_ROOT)}: from {node.module}")
    return offenders


class RepositoryArchitectureTests(unittest.TestCase):
    def test_no_tracked_autogen_rp_files(self) -> None:
        proc = subprocess.run(
            ["git", "ls-files", "autogen_rp"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(proc.stdout.strip(), "")

    def test_local_autogen_rp_tree_absent(self) -> None:
        self.assertFalse((_ROOT / "autogen_rp").exists())

    def test_gitignore_does_not_hide_legacy_autogen_rp(self) -> None:
        text = (_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertNotIn("autogen_rp/", text)

    def test_canonical_data_paths_module(self) -> None:
        source = Path(domain_paths.__file__).read_text(encoding="utf-8")
        self.assertNotIn("autogen_rp", source)
        self.assertNotIn("legacy_data_dir", source)
        self.assertNotIn("ensure_data_migrated", source)
        self.assertNotIn("data_migration", source)
        self.assertEqual(holy_grail_data_dir(), _ROOT / "data")

    def test_hg_data_dir_and_sessions_dir_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_data, tempfile.TemporaryDirectory() as tmp_sessions:
            with patch.dict(
                os.environ,
                {"HG_DATA_DIR": tmp_data, "HG_SESSIONS_DIR": tmp_sessions},
                clear=False,
            ):
                self.assertEqual(holy_grail_data_dir(), Path(tmp_data))
                self.assertEqual(characters_data_dir(), Path(tmp_data) / "characters")
                self.assertEqual(sessions_data_dir(), Path(tmp_sessions))
                repo = SessionRepository()
                kernel = DomainKernel(repository=repo)
                info = kernel.create_session(cast=["Alice", "Bob"])
            self.assertTrue((Path(tmp_sessions) / f"{info.hg_session_id}.json").is_file())

    def test_v2_production_has_no_autogen_imports(self) -> None:
        paths = _iter_python_files(_V2 / "domain_api", _V2 / "domain")
        self.assertEqual(_autogen_import_offenders(paths), [])

    def test_v2_production_has_no_legacy_orchestration_tokens(self) -> None:
        offenders: list[str] = []
        for tree_root in (_V2 / "domain_api", _V2 / "domain"):
            for path in tree_root.rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                for token in _PRODUCTION_FORBIDDEN_TOKENS:
                    if token in text:
                        offenders.append(f"{path.relative_to(_ROOT)}: {token}")
        self.assertEqual(offenders, [])

    def test_domain_modules_remain_framework_neutral(self) -> None:
        modules_dir = _V2 / "domain" / "modules"
        banned = ("autogen", "streamlit", "model_client", "turn_runner")
        offenders: list[str] = []
        for path in modules_dir.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    root = node.module.split(".")[0]
                    if root in banned:
                        offenders.append(f"{path.relative_to(_ROOT)}: from {node.module}")
        self.assertEqual(offenders, [])

    def test_active_tooling_has_no_rp_app_or_legacy_path_constants(self) -> None:
        offenders: list[str] = []
        for path in _iter_python_files(_TOOLS / "investigation", _TOOLS / "maintenance", _TOOLS):
            if path.name == "_repo_paths.py" and path.parent == _TOOLS:
                text = path.read_text(encoding="utf-8")
            else:
                text = path.read_text(encoding="utf-8")
            for token in ("LEGACY_RP_APP", "autogen_rp/python/rp_app", "sys.path.insert(0, str(LEGACY"):
                if token in text:
                    offenders.append(f"{path.relative_to(_ROOT)}: {token}")
        self.assertEqual(offenders, [])

    def test_investigation_tooling_present(self) -> None:
        self.assertTrue(_INV.is_dir())
        py_files = [p for p in _INV.glob("*.py") if p.name != "_repo_paths.py"]
        self.assertGreaterEqual(len(py_files), 8)
        helper = _TOOLS / "_repo_paths.py"
        text = helper.read_text(encoding="utf-8")
        self.assertIn("FIXTURES_DIR", text)
        self.assertIn("resolve_rp_audits_dir", text)
        self.assertNotIn("LEGACY_RP_APP", text)

    def test_compare_script_help(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(_INV / "compare_participation_calibration_ab.py"), "--help"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("baseline-summary", proc.stdout)

    def test_current_bootstrap_docs_avoid_retired_runtime_paths(self) -> None:
        """Current-facing docs must not instruct readers to use deleted V1 runtime trees."""
        doc_paths = [
            _ROOT / "README.md",
            _ROOT / "AGENTS.md",
            _ROOT / "governance" / "sources" / "architecture-overview.md",
            _ROOT / "governance" / "sources" / "holy-grail-prd.md",
            _ROOT / "MODULE_INDEX.md",
            _ROOT / "SCENARIO_VALIDATION_FRAMEWORK.md",
            _ROOT / "docs" / "architecture.md",
            _ROOT / "docs" / "repo-map.md",
            _ROOT / "docs" / "rp-data-layout.md",
            _ROOT / "docs" / "testing.md",
            _ROOT / "docs" / "core-operating-invariants.md",
            _ROOT / "v2" / "README.md",
        ]
        banned_substrings = (
            "autogen_rp/python/rp_app",
            "python/rp_app/",
            "scripts/run_scene_simulation_llm",
            "run_scene_simulation_llm.py",
            "LEGACY_RP_APP",
            "governance/archive/v1-runtime",
        )
        offenders: list[str] = []
        for path in doc_paths:
            text = path.read_text(encoding="utf-8")
            for token in banned_substrings:
                if token in text:
                    offenders.append(f"{path.relative_to(_ROOT)}: {token}")
        self.assertEqual(offenders, [])

    def test_no_legacy_migration_check_tool(self) -> None:
        self.assertFalse((_TOOLS / "maintenance" / "hg_data_migration_check.py").exists())

    def test_current_authority_surfaces_avoid_retired_instructional_paths(self) -> None:
        """Bootstrap/work-system authorities must not route to retired Autogen trees."""
        surfaces = list(_CURRENT_AUTHORITY_SURFACES)
        surfaces.extend(
            (
                _ROOT / "governance" / "sources" / "issue-tracking-workflow.md",
                _ROOT / "governance" / "sources" / "architecture-overview.md",
                _ROOT / "governance" / "sources" / "holy-grail-prd.md",
                _ROOT / "governance" / "execution" / "cursor-workflow-layer.md",
                _ROOT / "governance" / "execution" / "github-issues.md",
                _ROOT / "governance" / "sources" / "project-behavior-holy-grail.md",
                _ROOT / "governance" / "execution" / "rp-app-guidance.md",
                _ROOT / "governance" / "execution" / "architecture-protection.md",
                _ROOT / "governance" / "execution" / "testing-expectations.md",
            )
        )
        surfaces.extend(sorted((_ROOT / ".cursor" / "rules").glob("*.mdc")))
        banned = ("autogen_rp/", "python/rp_app/", "AUDIT_DOCUMENTATION.md")
        offenders: list[str] = []
        for path in surfaces:
            text = path.read_text(encoding="utf-8")
            for token in banned:
                if token in text:
                    offenders.append(f"{path.relative_to(_ROOT)}: {token}")
        self.assertEqual(offenders, [])

    def test_four_root_cursor_wrappers_exist_and_route_to_live_authorities(self) -> None:
        rules_dir = _ROOT / ".cursor" / "rules"
        expected = {
            "2-ai-system-start.mdc",
            "github-issues.mdc",
            "github-project-usage.mdc",
            "project-behavior.mdc",
        }
        actual = {p.name for p in rules_dir.glob("*.mdc")}
        self.assertEqual(actual, expected)
        routes = {
            "2-ai-system-start.mdc": "governance/execution/cursor-workflow-layer.md",
            "project-behavior.mdc": "governance/sources/project-behavior-holy-grail.md",
            "github-issues.mdc": "governance/execution/github-issues.md",
            "github-project-usage.mdc": "governance/sources/issue-tracking-workflow.md",
        }
        for name, target in routes.items():
            text = (rules_dir / name).read_text(encoding="utf-8")
            self.assertIn(target, text, name)
            self.assertNotIn("autogen_rp/", text, name)
            self.assertTrue((_ROOT / target).is_file(), target)
        project_wrapper = (rules_dir / "github-project-usage.mdc").read_text(encoding="utf-8")
        self.assertIn("§B", project_wrapper)

    def test_project_sync_root_cursor_wrappers_match_disk(self) -> None:
        manifest = tomllib.loads((_ROOT / "governance" / "project-sync.toml").read_text(encoding="utf-8"))
        listed = {row["basename"] for row in manifest.get("root_cursor_rule_files", [])}
        on_disk = {p.name for p in (_ROOT / ".cursor" / "rules").glob("*.mdc")}
        self.assertEqual(listed, on_disk)

    def test_bindings_work_system_identity_and_live_paths(self) -> None:
        bindings = tomllib.loads((_ROOT / "bindings" / "bindings.toml").read_text(encoding="utf-8"))
        github = bindings["github"]
        self.assertEqual(github["repository"], "KizzieFae/Holy-Grail-RP-DeepSeek-Harness")
        self.assertEqual(github["upstream_repository"], "KizzieFae/Holy_Grail_RP")
        self.assertEqual(github["project_owner"], "KizzieFae")
        self.assertEqual(github["project_number"], 10)
        self.assertEqual(github["project_name"], "Holy Grail RP — DSH")
        self.assertNotIn("project_url", github)
        self.assertEqual(bindings["agents"]["canonical_entrypoint"], "AGENTS.md")
        self.assertNotIn("python_workspace", bindings)
        self.assertNotIn("architecture_doc", bindings.get("issue_tracking", {}))
        raw = (_ROOT / "bindings" / "bindings.toml").read_text(encoding="utf-8")
        self.assertNotIn("autogen_rp", raw)
        issue_workflow_doc = bindings["issue_tracking"]["issue_workflow_doc"]
        self.assertTrue(
            issue_workflow_doc.startswith("governance/sources/"),
            issue_workflow_doc,
        )
        for rel in (
            bindings["agents"]["canonical_entrypoint"],
            issue_workflow_doc,
            bindings["issue_templates"]["config_path"],
            bindings["issue_templates"]["primary_form"],
            bindings["cursor_rules"]["workspace_root_rules"],
        ):
            self.assertTrue((_ROOT / rel).exists(), rel)

    def test_current_navigation_docs_avoid_retired_turn_loop_landings(self) -> None:
        """Current-system maps must not send operators to deleted Streamlit turn-loop files."""
        offenders: list[str] = []
        for path in _CURRENT_NAVIGATION_DOCS:
            text = path.read_text(encoding="utf-8")
            for token in _RETIRED_TURN_LOOP_LANDINGS:
                if token in text:
                    offenders.append(f"{path.relative_to(_ROOT)}: {token}")
        self.assertEqual(offenders, [])

    def test_current_navigation_docs_collectively_name_live_responsibility_roots(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in _CURRENT_NAVIGATION_DOCS)
        missing = [root for root in _LIVE_RESPONSIBILITY_ROOTS if root not in combined]
        self.assertEqual(missing, [])

    def test_current_navigation_surface_excludes_historical_governance_records(self) -> None:
        nav_rel = {path.relative_to(_ROOT).as_posix() for path in _CURRENT_NAVIGATION_DOCS}
        self.assertTrue(_GOVERNANCE_RECORDS_DIR.is_dir())
        leaked = [
            rel
            for rel in nav_rel
            if rel.startswith("governance/records/")
            and (
                rel.startswith("governance/records/v2-")
                or "/fresh-start-" in rel
                or "/round-a-" in rel
                or "/audit-classification-" in rel
                or "/failure-taxonomy-" in rel
            )
        ]
        self.assertEqual(leaked, [])
        for path in _CURRENT_NAVIGATION_DOCS:
            self.assertTrue(path.is_file(), path)

    def test_program_audit_semantics_and_procedure_authorities_exist(self) -> None:
        self.assertTrue(_AUDIT_SEMANTICS_PATH.is_file())
        self.assertTrue(_AUDIT_PROCEDURE_PATH.is_file())

    def test_audit_authority_nav_surfaces_point_to_live_semantics(self) -> None:
        semantics_ref = "governance/sources/audit-semantics.md"
        offenders: list[str] = []
        for path in _AUDIT_AUTHORITY_NAV_SURFACES:
            text = path.read_text(encoding="utf-8")
            if semantics_ref not in text:
                offenders.append(f"{path.relative_to(_ROOT)}: missing {semantics_ref}")
            if "audit interpretation" in text.lower():
                offenders.append(f"{path.relative_to(_ROOT)}: false audit interpretation label")
            if "AUDIT_DOCUMENTATION.md" in text:
                offenders.append(f"{path.relative_to(_ROOT)}: cites AUDIT_DOCUMENTATION.md")
        self.assertEqual(offenders, [])

    def test_audit_semantics_does_not_redefine_issue_workflow_tables(self) -> None:
        text = _AUDIT_SEMANTICS_PATH.read_text(encoding="utf-8")
        self.assertNotIn("| `open` |", text)
        self.assertNotIn("Project **Status**", text)
        self.assertNotIn("| P0 |", text)

    def test_governance_readme_defines_abcd_placement_convention(self) -> None:
        text = _GOVERNANCE_README_PATH.read_text(encoding="utf-8")
        self.assertIn("## Physical layout (A/B/C/D)", text)
        self.assertIn("## Creating governance documents", text)
        self.assertIn("governance/sources/", text)
        self.assertIn("governance/execution/", text)
        self.assertIn("governance/records/", text)
        sources_idx = text.index("## `sources/`")
        execution_idx = text.index("## `execution/`")
        records_idx = text.index("## `records/`")
        sources_section = text[sources_idx:execution_idx]
        self.assertIn("audit-semantics.md", sources_section)
        self.assertNotIn("audit-classification-protocol.md", sources_section)
        self.assertIn("HISTORICAL WORKSHOP", text)

    def test_historical_workshop_materials_carry_historical_banner(self) -> None:
        for path in _HISTORICAL_WORKSHOP_PATHS:
            text = path.read_text(encoding="utf-8")
            self.assertIn("HISTORICAL WORKSHOP", text, path.name)
            self.assertIn("audit-semantics.md", text, path.name)

    def test_read_only_program_audit_pathway_structural_guards(self) -> None:
        text = _AUDIT_SEMANTICS_PATH.read_text(encoding="utf-8")
        self.assertIn("## Read-only program audit", text)
        self.assertIn("read-only program audit", text)
        self.assertIn("**does not** require a GitHub Issue", text)
        self.assertIn("must **not**", text)
        self.assertIn("commit or push", text)
        self.assertIn("issue-tracking-workflow.md", text)
        self.assertIn("## Audit closure", text)
        self.assertIn("audit parent Issue", text)
        issue_tracking = (
            _ROOT / "governance" / "sources" / "issue-tracking-workflow.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Read-only program audit", issue_tracking)
        self.assertIn("audit-semantics.md", issue_tracking)
        project_behavior = (
            _ROOT / "governance" / "sources" / "project-behavior-holy-grail.md"
        ).read_text(encoding="utf-8")
        self.assertIn("read-only program audit", project_behavior.lower())


    def test_governance_sources_directory_is_minimum_upload_corpus(self) -> None:
        """Six files = current agreed project corpus (#10); not a permanent maximum."""
        self.assertTrue(_GOVERNANCE_SOURCES_DIR.is_dir())
        readme = _GOVERNANCE_README_PATH.read_text(encoding="utf-8")
        self.assertIn("minimum sufficient standing", readme.lower())
        self.assertIn("authoritative universal governance ai instruction set", readme.lower())
        on_disk = sorted(p.name for p in _GOVERNANCE_SOURCES_DIR.glob("*.md"))
        self.assertEqual(on_disk, sorted(_GOVERNANCE_CORPUS_FILES))
        for name in _GOVERNANCE_CORPUS_FILES:
            path = _GOVERNANCE_SOURCES_DIR / name
            self.assertTrue(path.is_file(), name)
            self.assertIn(name, readme)

    def test_retired_root_prd_and_architecture_paths_are_absent(self) -> None:
        self.assertFalse((_ROOT / "Holy Grail PRD.md").exists())
        self.assertFalse((_ROOT / "ARCHITECTURE_OVERVIEW.md").exists())

    def test_governance_corpus_avoids_instructional_v1_paths(self) -> None:
        banned = ("autogen_rp/", "python/rp_app/", "app_turn_")
        offenders: list[str] = []
        for name in _GOVERNANCE_CORPUS_FILES:
            text = (_GOVERNANCE_SOURCES_DIR / name).read_text(encoding="utf-8")
            for token in banned:
                if token in text:
                    offenders.append(f"governance/sources/{name}: {token}")
        self.assertEqual(offenders, [])

    def test_architecture_overview_contains_standing_invariants(self) -> None:
        text = (_GOVERNANCE_SOURCES_DIR / "architecture-overview.md").read_text(encoding="utf-8")
        self.assertIn("Standing architectural invariants", text)
        for phrase in (
            "Python domain code does not call DSH",
            "read-only projection",
            "non-authoritative",
            "Progression advisory",
            "scenario-grade validation",
        ):
            self.assertIn(phrase, text, phrase)

    def test_gpt_workflow_instruction_set_not_in_project_corpus(self) -> None:
        self.assertFalse((_GOVERNANCE_SOURCES_DIR / "gpt-workflow-instruction-set.md").exists())

    def test_project_sources_discover_read_only_audit_authority(self) -> None:
        readme = _GOVERNANCE_README_PATH.read_text(encoding="utf-8")
        project_behavior = (
            _GOVERNANCE_SOURCES_DIR / "project-behavior-holy-grail.md"
        ).read_text(encoding="utf-8")
        issue_tracking = (
            _ROOT / "governance" / "sources" / "issue-tracking-workflow.md"
        ).read_text(encoding="utf-8")
        self.assertIn("audit-semantics.md", readme)
        self.assertIn("read-only program audit", project_behavior.lower())
        self.assertIn("Read-only program audit", issue_tracking)
        self.assertIn("audit-semantics.md", issue_tracking)

    def test_live_navigation_avoids_removed_gpt_workflow_repo_path(self) -> None:
        nav_paths = [
            _ROOT / "README.md",
            _ROOT / "AGENTS.md",
            _GOVERNANCE_README_PATH,
            _GOVERNANCE_SOURCES_DIR / "workflow-weights.md",
            _GOVERNANCE_SOURCES_DIR / "issue-tracking-workflow.md",
            _ROOT / "governance" / "execution" / "cursor-workflow-layer.md",
            _ROOT / ".github" / "ISSUE_TEMPLATE" / "holy_grail_rp.yml",
        ]
        offenders: list[str] = []
        for path in nav_paths:
            if _REMOVED_GPT_WORKFLOW_REPO_PATH in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(_ROOT)))
        self.assertEqual(offenders, [])

    def test_governance_source_corpus_avoids_autogen_as_current_architecture(self) -> None:
        banned = ("AutoGen / runtime", "autogen_rp/", "python/rp_app/", "app_turn_")
        offenders: list[str] = []
        for name in _GOVERNANCE_CORPUS_FILES:
            text = (_GOVERNANCE_SOURCES_DIR / name).read_text(encoding="utf-8")
            for token in banned:
                if token in text:
                    offenders.append(f"governance/sources/{name}: {token}")
        self.assertEqual(offenders, [])

    def test_root_agents_is_bootstrap_not_governance_corpus_duplicate(self) -> None:
        self.assertTrue((_ROOT / "AGENTS.md").is_file())
        self.assertFalse((_GOVERNANCE_SOURCES_DIR / "agents.md").exists())
        agents = (_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("governance/sources/", agents)
        self.assertIn("upload corpus", agents.lower())

    def test_governance_sources_directory_is_canonical_authority_root(self) -> None:
        self.test_governance_sources_directory_is_minimum_upload_corpus()

    def test_project_sync_governance_documents_resolve(self) -> None:
        manifest = tomllib.loads((_ROOT / "governance" / "project-sync.toml").read_text(encoding="utf-8"))
        missing = [
            row["path"]
            for row in manifest.get("governance_policy_documents", [])
            if not (_ROOT / row["path"]).is_file()
        ]
        self.assertEqual(missing, [])

    def test_current_authority_surfaces_avoid_retired_governance_paths(self) -> None:
        surfaces = [
            path
            for path in _CURRENT_AUTHORITY_SURFACES
            if path not in {_ROOT / "AGENTS.md", _GOVERNANCE_README_PATH}
        ]
        surfaces.extend(sorted((_ROOT / ".cursor" / "rules").glob("*.mdc")))
        offenders: list[str] = []
        for path in surfaces:
            text = path.read_text(encoding="utf-8")
            for prefix in _RETIRED_GOVERNANCE_PATH_PREFIXES:
                if prefix in text:
                    offenders.append(f"{path.relative_to(_ROOT)}: {prefix}")
        self.assertEqual(offenders, [])

    def test_retired_governance_directories_are_absent(self) -> None:
        for rel in ("governance/policies", "governance/rp-app", "governance/github"):
            self.assertFalse((_ROOT / rel).exists(), rel)

    def test_contract_authority_docs_avoid_instructional_v1_paths(self) -> None:
        banned = ("autogen_rp/", "python/rp_app/", "app_turn_")
        offenders: list[str] = []
        for path in _CONTRACT_AUTHORITY_DOCS:
            text = path.read_text(encoding="utf-8")
            for token in banned:
                if token in text:
                    offenders.append(f"{path.relative_to(_ROOT)}: {token}")
        self.assertEqual(offenders, [])

    def test_character_context_manifest_projects_rp_history(self) -> None:
        projection = _V2 / "domain_api" / "character_conversation_projection.py"
        self.assertTrue(projection.is_file())
        kernel_text = (_V2 / "domain_api" / "kernel.py").read_text(encoding="utf-8")
        self.assertIn("project_character_conversation_for_manifest", kernel_text)
        self.assertIn("recent_scene_transcript", kernel_text)
        contract_text = (_V2 / "domain_api" / "contract.py").read_text(encoding="utf-8")
        self.assertIn("recent_scene_transcript", contract_text)
        self.assertIn("user_turn_trigger", contract_text)

    def test_deleted_root_duplicate_docs_absent(self) -> None:
        missing = [rel for rel in _DELETED_ROOT_DOC_PATHS if (_ROOT / rel).exists()]
        self.assertEqual(missing, [])

    def test_issue9_relocated_records_carry_historical_banner(self) -> None:
        for path in _ISSUE9_RELOCATED_RECORDS:
            text = path.read_text(encoding="utf-8")
            self.assertIn("HISTORICAL RECORD", text, path.name)

    def test_live_navigation_avoids_deleted_root_doc_paths(self) -> None:
        nav_paths = [
            _ROOT / "README.md",
            _ROOT / "AGENTS.md",
            _ROOT / "MODULE_INDEX.md",
            _ROOT / "docs" / "repo-map.md",
            _ROOT / "docs" / "rp-data-layout.md",
            _GOVERNANCE_SOURCES_DIR / "architecture-overview.md",
            _GOVERNANCE_SOURCES_DIR / "workflow-weights.md",
        ]
        offenders: list[str] = []
        root_roadmap = re.compile(r"(?<![/-])roadmap\.md")
        for path in nav_paths:
            text = path.read_text(encoding="utf-8")
            for token in _DELETED_ROOT_DOC_PATHS:
                if token == "roadmap.md":
                    continue
                if token in text:
                    offenders.append(f"{path.relative_to(_ROOT)}: {token}")
            if root_roadmap.search(text):
                offenders.append(f"{path.relative_to(_ROOT)}: roadmap.md")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
