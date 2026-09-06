"""Issue #136 — Director/Character inference_instruction ownership deduplication."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.contract import ContextPrepareRequest, DirectorContextPrepareRequest, RoundStartRequest  # noqa: E402
from domain_api.kernel import DomainKernel  # noqa: E402

APPROVED_CHARACTER_INVARIANT = (
    "Ground this turn's beats and motivation in the authoritative Character and "
    "scene context already supplied; action, inaction, and change should follow "
    "from that context."
)

DIRECTOR_DSH_FORBIDDEN = ("next_actor", "end_round", "tension_shift", "environment_event")
CHARACTER_DSH_FORBIDDEN = ("move_schema_version", "beats", "risk_level")


def _load_dsh_transport_prompts() -> dict[str, str]:
    script = _V2 / "rp_runtime" / "scripts" / "export-live-inference-prompts.mjs"
    if not script.exists():
        # Inline fallback for environments without the export helper.
        prompts_path = _V2 / "rp_runtime" / "src" / "lib" / "live-inference-prompts.mjs"
        text = prompts_path.read_text(encoding="utf-8")
        director = character = None
        for line in text.splitlines():
            if "LIVE_INFERENCE_TRANSPORT_PROMPT" in line and "=" in line:
                director = character = line.split("=", 1)[1].strip().strip("'").strip(";")
                break
        if director is None:
            raise RuntimeError("Could not parse live-inference-prompts.mjs")
        return {"director": director, "character": character}
    result = subprocess.run(
        ["node", str(script)],
        check=True,
        capture_output=True,
        text=True,
        cwd=_V2 / "rp_runtime",
    )
    return json.loads(result.stdout)


class Issue136InferenceInstructionOwnershipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = DomainKernel.for_fixture_store()
        self.scene_id = self.kernel.create_scene().hg_scene_id
        self.rnd_id = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=self.scene_id)
        ).hg_round_id

    def _director_instruction(self) -> str:
        manifest = self.kernel.prepare_director_context(
            DirectorContextPrepareRequest(
                hg_scene_id=self.scene_id,
                hg_round_id=self.rnd_id,
                inference_id="inf-dir-136",
                turn_index=0,
                attempt_index=0,
            )
        )
        instruction = next(
            c for c in manifest.contributions if c.source_kind == "inference_instruction"
        )
        return instruction.content

    def _director_scratch(self) -> str:
        manifest = self.kernel.prepare_director_context(
            DirectorContextPrepareRequest(
                hg_scene_id=self.scene_id,
                hg_round_id=self.rnd_id,
                inference_id="inf-dir-136-scratch",
                turn_index=0,
                attempt_index=0,
            )
        )
        scratch = next(c for c in manifest.contributions if c.source_kind == "director_scratch")
        return scratch.content

    def _character_instruction(self) -> str:
        manifest = self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=self.scene_id,
                hg_round_id=self.rnd_id,
                inference_id="inf-char-136",
                character_id="Alice",
                role="guest",
                turn_index=0,
                attempt_index=0,
            )
        )
        instruction = next(
            c for c in manifest.contributions if c.source_kind == "inference_instruction"
        )
        return instruction.content

    def test_director_host_contract_contains_schema_and_domain_requirements(self) -> None:
        text = self._director_instruction().lower()
        for token in ("next_actor", "end_round", "reason", "environment_event", "tension_shift"):
            self.assertIn(token, text)
        self.assertIn("escalate", text)
        self.assertIn("soften", text)
        self.assertIn("steady", text)
        self.assertIn("empty string", text)
        self.assertIn("eligible cast", text)
        self.assertIn("end_round to false", text)

    def test_director_scratch_retains_selection_guidance(self) -> None:
        scratch = self._director_scratch().lower()
        self.assertIn("participation balance", scratch)
        self.assertIn("eligible cast", scratch)
        self.assertIn("end_round", scratch)
        self.assertIn("character-private knowledge", scratch)

    def test_character_host_contract_contains_schema_and_invariant(self) -> None:
        text = self._character_instruction()
        lower = text.lower()
        self.assertIn("move_schema_version 2", lower)
        self.assertIn("beats", lower)
        self.assertIn("motivation", lower)
        self.assertIn("semantic_evaluation", lower)
        self.assertIn("type action", lower)
        self.assertIn("type speech", lower)
        self.assertIn("risk_level", lower)
        for level in ("low", "medium", "high"):
            self.assertIn(level, lower)
        self.assertIn(APPROVED_CHARACTER_INVARIANT, text)

    def test_dsh_transport_prompts_are_minimal_and_non_duplicative(self) -> None:
        prompts = _load_dsh_transport_prompts()
        for role, prompt in prompts.items():
            lower = prompt.lower()
            self.assertIn("json object", lower)
            self.assertNotIn("markdown", lower.replace("no markdown", ""))
            forbidden = DIRECTOR_DSH_FORBIDDEN if role == "director" else CHARACTER_DSH_FORBIDDEN
            for token in forbidden:
                self.assertNotIn(token, lower, msg=f"{role} DSH must not repeat Host contract token {token}")
            self.assertNotIn("manifest", lower)
            self.assertNotIn("inference_instruction", lower)


if __name__ == "__main__":
    unittest.main()
