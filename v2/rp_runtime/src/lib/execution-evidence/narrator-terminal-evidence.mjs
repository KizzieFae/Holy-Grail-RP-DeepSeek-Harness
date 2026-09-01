/**
 * Observational post-persistence association for Narrator terminal presentation (#93).
 */

/**
 * @param {import('./recorder.mjs').ExecutionEvidenceRecorder | null | undefined} recorder
 * @param {object} params
 * @param {string} params.hgSessionId
 * @param {string | null | undefined} params.narratorEvidenceId
 * @param {object | null | undefined} params.presentationEntry
 */
export function patchNarratorTerminalPresentationEvidence(recorder, {
  hgSessionId,
  narratorEvidenceId,
  presentationEntry,
}) {
  if (!recorder?.isEnabled?.() || !hgSessionId || !narratorEvidenceId || !presentationEntry) {
    return;
  }
  const metadata = presentationEntry.metadata ?? {};
  recorder.patchDecision(narratorEvidenceId, hgSessionId, {
    associations: {
      presentation_entry_id: presentationEntry.entry_id ?? null,
    },
    decision: {
      terminal_presentation: {
        text: presentationEntry.content ?? null,
        presentation_source: metadata.presentation_source ?? null,
        presentation_degraded: Boolean(metadata.presentation_degraded),
      },
    },
  });
}
