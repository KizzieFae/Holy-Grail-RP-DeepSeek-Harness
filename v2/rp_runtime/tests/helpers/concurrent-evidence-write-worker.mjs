import { ExecutionEvidenceStore } from '../../src/lib/execution-evidence/store.mjs';

const [root, hgSessionId, evidenceId] = process.argv.slice(2);
if (!root || !hgSessionId || !evidenceId) {
  throw new Error('usage: concurrent-evidence-write-worker.mjs <root> <hgSessionId> <evidenceId>');
}

const store = new ExecutionEvidenceStore(root);
store.writeAttempt({
  evidence_id: evidenceId,
  correlation: {
    evidence_id: evidenceId,
    hg_session_id: hgSessionId,
    hg_scene_id: hgSessionId,
    hg_round_id: 'round-concurrent',
    inference_id: evidenceId,
    inference_kind: 'narrator_environment_cognition',
  },
  request: { schema: 'hg_assembled_request_v1', contributions: [] },
  response: { schema: 'hg_model_response_v1', assistant_text: '{}' },
});
