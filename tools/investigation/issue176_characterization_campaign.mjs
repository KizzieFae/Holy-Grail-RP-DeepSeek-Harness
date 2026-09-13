#!/usr/bin/env node
/**
 * Issue #176 robust Layer B critical-path characterization campaign.
 * Application-bound live sessions with post-#173 orchestration instrumentation.
 *
 * Usage (from repo root):
 *   node tools/investigation/issue176_characterization_campaign.mjs
 *   node tools/investigation/issue176_characterization_campaign.mjs --condition baseline --rep 1
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { HolyGrailApplicationClient } from '../../v2/rp_runtime/src/application/hg-application-client.mjs';
import { hasLiveApiKey } from '../../v2/rp_runtime/src/scenario-harness/live-config.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../..');

const CONDITIONS = [
  {
    id: 'baseline',
    description: 'Two-character cast; ordinary turn flow; moderate overlay/candidate pressure (prototype cast mode)',
    session: { cast: ['Alice', 'Bob'], location: 'Household evaluation room' },
    userTurns: [
      'I answer the other character calmly and try to keep the conversation constructive.',
      'I listen, then respond with a clear point that moves the scene forward without escalating.',
      'I adjust my tone and state my position respectfully while staying engaged in the exchange.',
    ],
  },
  {
    id: 'stress',
    description: 'Three-character cast; higher per-round interaction density and director cycling',
    session: { cast: ['Alice', 'Bob', 'Carol'], location: 'Shared quarters under tension' },
    userTurns: [
      'I acknowledge the awkward situation and ask how we can make the shared space workable.',
      'I respond to whichever character addresses me, trying to reduce friction between the others.',
      'I propose a concrete next step that respects everyone in the room.',
      'I stay present and answer the follow-up without withdrawing from the conflict.',
    ],
  },
  {
    id: 'variant',
    description: 'Two-character cast; extended four-turn session for deeper overlay evolution vs baseline',
    session: { cast: ['Alice', 'Bob'], location: 'Quiet apartment after an incident' },
    userTurns: [
      'I speak softly and reassure the other character I am cooperating.',
      'I answer their question directly and show I understand what is at stake.',
      'I make a small gesture of trust without overcommitting.',
      'I respond to the latest development with measured honesty.',
    ],
  },
];

const REPS_PER_CONDITION = 3;

const USER_MESSAGES_DEFAULT = [
  'I respond thoughtfully to what was just said and try to move the scene forward.',
  'I listen, then offer a measured reply that respects the other characters in the room.',
  'I clarify my position calmly without escalating the situation.',
];

function repoSha() {
  try {
    return execSync('git rev-parse HEAD', { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  } catch {
    return 'unknown';
  }
}

function parseArgs(argv) {
  const out = { condition: null, rep: null, dryRun: false };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--condition' && argv[i + 1]) {
      out.condition = argv[++i];
    } else if (argv[i] === '--rep' && argv[i + 1]) {
      out.rep = Number(argv[++i]);
    } else if (argv[i] === '--dry-run') {
      out.dryRun = true;
    }
  }
  return out;
}

function campaignRoot() {
  const stamp = process.env.ISSUE176_CAMPAIGN_STAMP
    ?? new Date().toISOString().replace(/[:.]/g, '-');
  return path.join(REPO_ROOT, 'data', 'investigation_runs', `issue176-characterization-${stamp}`);
}

async function runSingleSession({ condition, rep, runRoot, repoSha: sha }) {
  fs.mkdirSync(runRoot, { recursive: true });
  const sessionsDir = path.join(runRoot, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const evidenceRoot = path.join(runRoot, 'execution_evidence');
  fs.mkdirSync(evidenceRoot, { recursive: true });

  const mainDataDir = path.join(REPO_ROOT, 'data');
  const prev = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_SESSIONS_DIR: process.env.HG_SESSIONS_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
    HG_EXECUTION_EVIDENCE_DIR: process.env.HG_EXECUTION_EVIDENCE_DIR,
  };
  process.env.HG_DATA_DIR = mainDataDir;
  process.env.HG_SESSIONS_DIR = sessionsDir;
  process.env.HG_EXECUTION_EVIDENCE = 'on';
  process.env.HG_EXECUTION_EVIDENCE_DIR = evidenceRoot;

  const client = new HolyGrailApplicationClient({
    inferenceMode: 'live',
    domainHost: { sessionsDir },
    runtime: { inference: { mountDeepSeek: true, executionEvidence: { enabled: true, root: evidenceRoot } } },
  });

  const startedAt = new Date().toISOString();
  let sessionId = null;
  const turnRecords = [];

  try {
    await client.start();
    const session = await client.createSession({
      ...condition.session,
      opening: { mode: 'generated' },
    });
    sessionId = session.hg_session_id;

    const messages = condition.userTurns?.length ? condition.userTurns : USER_MESSAGES_DEFAULT;
    for (let i = 0; i < messages.length; i += 1) {
      const turnStarted = Date.now();
      const turn = await client.submitUserTurn({ userMessage: messages[i] });
      turnRecords.push({
        turn_index: i,
        user_message: messages[i],
        client_operation_id: turn.client_operation_id,
        hg_round_id: turn.round?.hg_round_id ?? null,
        character_turn_count: turn.round?.character_turns?.length ?? 0,
        completion_reason: turn.round?.completion_reason ?? null,
        wall_ms: Date.now() - turnStarted,
      });
    }
    await client.stop();
  } finally {
    for (const [key, value] of Object.entries(prev)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }

  const manifest = {
    schema: 'issue176_characterization_run_v1',
    condition_id: condition.id,
    condition_description: condition.description,
    repetition: rep,
    repo_sha: sha,
    started_at: startedAt,
    completed_at: new Date().toISOString(),
    session_config: condition.session,
    hg_session_id: sessionId,
    data_dir: runRoot,
    execution_evidence_dir: evidenceRoot,
    user_turns: turnRecords,
  };
  fs.writeFileSync(path.join(runRoot, 'run_manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
  return manifest;
}

async function main() {
  if (!hasLiveApiKey()) {
    console.error('DEEPSEEK_API_KEY not set');
    process.exit(2);
  }

  const args = parseArgs(process.argv.slice(2));
  const sha = repoSha();
  const root = campaignRoot();
  fs.mkdirSync(root, { recursive: true });

  const matrix = [];
  for (const condition of CONDITIONS) {
    if (args.condition && args.condition !== condition.id) continue;
    for (let rep = 1; rep <= REPS_PER_CONDITION; rep += 1) {
      if (args.rep != null && args.rep !== rep) continue;
      matrix.push({ condition, rep });
    }
  }

  const campaignManifest = {
    schema: 'issue176_characterization_campaign_v1',
    repo_sha: sha,
    campaign_root: root,
    repetitions_per_condition: REPS_PER_CONDITION,
    conditions: CONDITIONS.map((c) => ({ id: c.id, description: c.description, session: c.session })),
    note: 'Prototype cast mode (no local character cards); scene templates not required. Isolated sessions + EE per run.',
    planned_runs: matrix.length,
    governance_challenge: 'Robust post-#173 Layer B critical-path characterization',
  };
  fs.writeFileSync(path.join(root, 'campaign_manifest.json'), `${JSON.stringify(campaignManifest, null, 2)}\n`);

  if (args.dryRun) {
    console.log(JSON.stringify({ campaign_root: root, planned_runs: matrix }, null, 2));
    return;
  }

  const results = [];
  for (const { condition, rep } of matrix) {
    const runId = `${condition.id}-rep${String(rep).padStart(2, '0')}-${crypto.randomUUID().slice(0, 8)}`;
    const runRoot = path.join(root, condition.id, `rep-${String(rep).padStart(2, '0')}`, runId);
    console.log(`[issue176] starting ${runId} (${condition.id} rep ${rep})`);
    const manifest = await runSingleSession({ condition, rep, runRoot, repoSha: sha });
    results.push(manifest);
    console.log(`[issue176] completed ${runId} session=${manifest.hg_session_id}`);
  }

  campaignManifest.completed_at = new Date().toISOString();
  campaignManifest.runs = results;
  fs.writeFileSync(path.join(root, 'campaign_manifest.json'), `${JSON.stringify(campaignManifest, null, 2)}\n`);
  console.log(JSON.stringify({ campaign_root: root, runs_completed: results.length }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
