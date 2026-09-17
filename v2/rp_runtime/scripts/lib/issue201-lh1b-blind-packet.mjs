/**
 * Issue #201 LH-1B — blind packet builder (secondary evaluation readiness).
 * Requires live sequence presentations; does not emit placeholders.
 */
import { LH1B_SCHEMAS, LH1B_BLIND_FORBIDDEN_PATTERNS } from './issue201-lh1b-contract.mjs';

export function buildLh1bBlindPacket({ campaignPlan, rubric = null, sequenceArtifacts = [] }) {
  const artifactByLabel = new Map((sequenceArtifacts ?? []).map((s) => [s.blind_label, s]));
  const sequences = campaignPlan.sequences.map((seq) => {
    const artifact = artifactByLabel.get(seq.blind_label);
    const turns = (artifact?.turns ?? seq.turns).map((t) => ({
      turn_index: t.turn_index,
      player_stimulus: t.exact_player_stimulus ?? t.player_stimulus,
      presentation_text: t.presentation_text ?? null,
    }));
    if (turns.some((t) => !t.presentation_text)) {
      throw new Error(`LH-1B blind packet missing presentation for ${seq.blind_label}`);
    }
    return {
      blind_label: seq.blind_label,
      turn_count: seq.turn_count,
      turns,
    };
  });
  return {
    schema: LH1B_SCHEMAS.BLIND_PACKET,
    purpose: 'Issue #201 LH-1B optional secondary blind evaluation',
    sequences,
    rubric_id: rubric?.rubric_id ?? null,
  };
}

export function validateLh1bBlindPacketIntegrity(packet) {
  const packetText = JSON.stringify(packet).toLowerCase();
  const leaked = LH1B_BLIND_FORBIDDEN_PATTERNS
    .filter((re) => re.test(packetText))
    .map((re) => re.source);
  const hasPlaceholder = packet.sequences?.some((s) => (
    s.turns?.some((t) => String(t.presentation_text ?? '').includes('apparatus validation'))
  ));
  if (hasPlaceholder) leaked.push('placeholder_presentation_text');
  return {
    pass: leaked.length === 0,
    leaked_patterns: leaked,
    sequence_count: packet.sequences?.length ?? 0,
  };
}
