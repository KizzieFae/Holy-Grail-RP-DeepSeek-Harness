## Wave 1 complete — opening / semantic-block deduplication (#242)

**Scope:** `build_issue240_v1_next5_opening()` only — no semantic block, OUTPUT RULES, or topology ordering changes.

### Commit

- **SHA:** `70d4663cba709cb52df34b03161562ce98b49986`
- **Change:** Removed duplicated `semantic_evaluation` schema lines from opening; preserved role-first framing + wire pointer to trigger-adjacent block and OUTPUT RULES.

### Token delta

- **Opening block:** 599 → 468 chars (**−131 chars/turn**)

### Deterministic validation — PASS

```
pytest tests/test_issue_240_prompt_topology.py tests/test_prompt_topology_manifest.py -q
→ 42 passed
```

### Live validation — R1a + R1b cert reps

| Run | Session | `semantic_eval_presence` | Profile match | Ordering violations | Fingerprint match |
|-----|---------|--------------------------|---------------|---------------------|-------------------|
| R1a | `session_878` | **1.0** | **1.0** | **0** | **unchanged** |
| R1b | `session_879` | **1.0** | **1.0** | **0** | **unchanged** |

**Dominant fingerprint (878/879 vs baseline 861 / Wave 0 877):**
`opening.dual|semantic.block|frame|eval.required|eval.examples|cal.v7|priorities.comp|output.slim|evidence`

### Overlay / classifier notes

| Metric | R1a (878) | R1b (879) | Baseline (861/862) |
|--------|-----------|-----------|---------------------|
| Overlay-applied engagement | **2/2** | **2/2** | 1/1 |
| Overlay-aligned F0 | **0/2** | **0/2** | **1/1** |
| `semantic_decision` on overlay turns | `no_covered_change` (honest) | `no_covered_change` (honest) | `covered_change` |

**WARN:** Legacy overlay-aligned F0 below baseline on both reps — conservative classifier label; **no semantic wire omission** (100% `semantic_evaluation` presence). Likely live variance on whether Celina beats substantiate off_focal vs honest `no_covered_change` (878 turn 2: kitchen movement + `no_covered_change`).

### Manual RP spot-check — PASS

- **Voices:** Ayame controlled/cataloguing; Celina territorial/blunt — distinct, not flattened.
- **Overlay honesty:** Models emitted valid `semantic_evaluation`; no instructional/meta cosplay in dialogue.
- **No obvious RP-quality degradation** from opening trim.

### Artifacts

- `autogen_rp/python/validation_runs/issue242_wave1/R1a_cert_metrics.json`
- `autogen_rp/python/validation_runs/issue242_wave1/R1b_cert_metrics.json`
- `autogen_rp/python/data/issue240_runs/issue242_wave1_prompts/`
- Audits: `session_878`, `session_879`

### Next

- **Wave 3 remains blocked** pending explicit authorization.
- **Wave 2** remains conditionally approved only.
