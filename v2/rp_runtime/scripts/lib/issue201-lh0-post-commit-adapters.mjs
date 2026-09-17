/**
 * Issue #201 LH-0 — live persistent cognition post-commit adapters (harness-only).
 */
import crypto from 'node:crypto';

import { LH0_ARMS } from './issue201-lh0-arms.mjs';
import { runPostCommitPlotCognitionLifecycle } from '../../src/lib/plot-cognition-orchestration.mjs';
import {
  readLh0Store,
  writeLh0Store,
  upsertLh0Obligation,
} from './issue201-lh0-persistent-store.mjs';
import { loadLh0FixtureManifest } from './issue201-lh0-fixtures.mjs';
import { seedLh0ObligationFromFixture } from './issue201-lh0-semantic-content.mjs';

function buildPersistentPrompt({ arm, fixtureObligations, turnIndex, presentationText }) {
  const armLabel = arm === LH0_ARMS.LH_C ? 'persistent Storyteller-class' : 'consolidated narrative intelligence';
  return [
    `You are ${armLabel} cognition for LH-0 seam verification.`,
    'Return ONLY valid JSON: {"obligations":[{"obligation_id":"...","summary":"...","obligation_text":"...","authorized_consumer":"character_move|director_turn","activation_predicate":{"type":"turn_gte","value":N},"activation_horizon_turn":N,"deferral_rationale":null,"negative_control":false}]}',
    `Turn: ${turnIndex}`,
    `Fixture obligations (stable IDs required): ${JSON.stringify(fixtureObligations)}`,
    `Latest presentation excerpt: ${String(presentationText ?? '').slice(0, 1500)}`,
    'Track unresolved narrative obligations. Do not resolve negative_control obligations early.',
  ].join('\n');
}

export function buildLh0HarnessInferenceManifest({ inferenceId, mechanism, prompt }) {
  const sourceKind = mechanism === 'plot_cognition_update' ? 'active_constraints' : 'inference_instruction';
  return {
    manifest_id: `lh0-harness-${inferenceId}`,
    inference_kind: mechanism,
    inference_id: inferenceId,
    contributions: [{
      contribution_id: `${inferenceId}-lh0-harness`,
      source_kind: sourceKind,
      authority_class: 'derived',
      content: prompt,
      knowledge_ids: [`inference:${inferenceId}`],
      provenance: { inference_id: inferenceId, lh0_harness: true },
    }],
  };
}

function parseObligationJson(raw) {
  if (!raw) return [];
  const text = typeof raw === 'string' ? raw : JSON.stringify(raw);
  const match = text.match(/\{[\s\S]*\}/);
  if (!match) return [];
  try {
    const parsed = JSON.parse(match[0]);
    return Array.isArray(parsed.obligations) ? parsed.obligations : [];
  } catch {
    return [];
  }
}

function obligationsForPostCommitSeed(fixture, fixtureTurnIndex) {
  if (fixture.schema === 'issue201_lh1a_fixture_manifest_v1'
    || fixture.schema === 'issue201_lh1b_fixture_manifest_v1') {
    return fixture.obligations.filter((o) => (o.intro_turn ?? 1) <= fixtureTurnIndex);
  }
  return fixture.obligations;
}

export async function runLh0PostCommitAdapter({
  arm,
  domainApi,
  trace,
  sceneAgent,
  scope,
  hgSceneId,
  hgRoundId,
  hgSessionId,
  domainCommitId,
  turnIndex,
  fixtureTurnIndex = turnIndex,
  runtimeTurnIndex = null,
  presentationText,
  sessionsDir,
  runEphemeralInference,
  modelProfile,
  evidenceContextBase,
  fixtureManifest = null,
}) {
  const fixture = fixtureManifest ?? loadLh0FixtureManifest();
  const inferenceId = `lh0-persist-${arm}-${crypto.randomUUID()}`;

  if (arm === LH0_ARMS.LH_B) {
    const plotResult = await runPostCommitPlotCognitionLifecycle({
      domainApi,
      trace,
      sceneAgent,
      scope: { ...scope, hgRoundId },
      hgSceneId,
      inferenceId,
      runEphemeralInference,
      modelProfile,
      evidenceContextBase: {
        ...evidenceContextBase,
        lh0_fixture_id: fixture.fixture_id,
        lh0_obligations: fixture.obligations,
      },
    });
    const store = readLh0Store(sessionsDir, hgSessionId);
    for (const fo of obligationsForPostCommitSeed(fixture, fixtureTurnIndex)) {
      upsertLh0Obligation(store, seedLh0ObligationFromFixture(fo, {
        mechanism: 'plot_cognition_update',
        source: 'live_plot_scribe',
      }), { turn: fixtureTurnIndex, inferenceId, mechanism: 'plot_cognition_update' });
    }
    writeLh0Store(sessionsDir, hgSessionId, store);
    return {
      adapter: 'plot_scribe',
      ok: plotResult?.ok !== false,
      plot_post_commit: plotResult,
      inference_id: inferenceId,
      live_cognition: true,
      fixture_turn_index: fixtureTurnIndex,
      runtime_turn_index: runtimeTurnIndex,
    };
  }

  const prompt = buildPersistentPrompt({
    arm,
    fixtureObligations: fixture.obligations,
    turnIndex: fixtureTurnIndex,
    presentationText,
  });
  const mechanism = arm === LH0_ARMS.LH_C
    ? 'storyteller_post_commit_issue_pressure'
    : 'plot_cognition_update';
  const evidenceMechanism = arm === LH0_ARMS.LH_C
    ? 'persistent_storyteller_agenda'
    : 'consolidated_narrative_intelligence';

  const manifest = buildLh0HarnessInferenceManifest({ inferenceId, mechanism, prompt });
  const inference = await runEphemeralInference({
    inferenceId,
    prompt,
    manifest,
    modelProfile,
    evidenceContext: {
      ...evidenceContextBase,
      inferenceKind: mechanism,
      role: 'storyteller',
      parentInferenceId: inferenceId,
      lh0_harness_post_commit: true,
    },
  });

  const obligations = parseObligationJson(inference?.raw_output ?? inference?.text ?? inference);
  const store = readLh0Store(sessionsDir, hgSessionId);
  for (const ob of obligations) {
    upsertLh0Obligation(store, ob, { turn: fixtureTurnIndex, inferenceId, mechanism });
  }
  if (!obligations.length) {
    for (const fo of obligationsForPostCommitSeed(fixture, fixtureTurnIndex)) {
      upsertLh0Obligation(store, seedLh0ObligationFromFixture(fo, {
        mechanism: evidenceMechanism,
        source: 'fixture_seed',
      }), { turn: fixtureTurnIndex, inferenceId, mechanism: evidenceMechanism });
    }
  }
  writeLh0Store(sessionsDir, hgSessionId, store);
  return {
    adapter: evidenceMechanism,
    ok: true,
    inference_id: inferenceId,
    obligation_count: store.obligations.length,
    live_cognition: true,
    token_accounting: inference?.token_accounting ?? null,
    fixture_turn_index: fixtureTurnIndex,
    runtime_turn_index: runtimeTurnIndex,
  };
}
