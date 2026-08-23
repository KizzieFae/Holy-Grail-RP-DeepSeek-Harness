import fs from 'node:fs';
import path from 'node:path';

import { ATTEMPT_SCHEMA, INDEX_SCHEMA } from './config.mjs';

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function writeJsonAtomic(filePath, value) {
  ensureDir(path.dirname(filePath));
  const tempPath = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(tempPath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  fs.renameSync(tempPath, filePath);
}

function readJsonIfExists(filePath) {
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

/**
 * Low-level HG-native execution evidence persistence.
 */
export class ExecutionEvidenceStore {
  /**
   * @param {string} root
   */
  constructor(root) {
    this.root = path.resolve(root);
  }

  sessionDir(hgSessionId) {
    return path.join(this.root, String(hgSessionId));
  }

  indexPath(hgSessionId) {
    return path.join(this.sessionDir(hgSessionId), 'index.json');
  }

  attemptPath(hgSessionId, evidenceId) {
    return path.join(this.sessionDir(hgSessionId), 'attempts', `${evidenceId}.json`);
  }

  /**
   * @param {object} attempt
   * @returns {string} evidence_id
   */
  writeAttempt(attempt) {
    const hgSessionId = String(attempt.correlation.hg_session_id);
    const evidenceId = String(attempt.evidence_id);
    const sessionDir = this.sessionDir(hgSessionId);
    ensureDir(path.join(sessionDir, 'attempts'));

    const payload = {
      schema: ATTEMPT_SCHEMA,
      ...attempt,
      recorded_at: attempt.recorded_at ?? new Date().toISOString(),
    };
    writeJsonAtomic(this.attemptPath(hgSessionId, evidenceId), payload);
    this._indexAttempt(hgSessionId, evidenceId, attempt.correlation);
    return evidenceId;
  }

  /**
   * @param {string} hgSessionId
   * @param {string} evidenceId
   * @param {object} patch
   */
  patchAttempt(hgSessionId, evidenceId, patch) {
    const filePath = this.attemptPath(hgSessionId, evidenceId);
    const current = readJsonIfExists(filePath);
    if (!current) return;
    const next = {
      ...current,
      ...patch,
      decision: {
        ...(current.decision ?? {}),
        ...(patch.decision ?? {}),
      },
      associations: {
        ...(current.associations ?? {}),
        ...(patch.associations ?? {}),
      },
      updated_at: new Date().toISOString(),
    };
    writeJsonAtomic(filePath, next);
    this._indexSemanticDecision(hgSessionId, evidenceId, next);
  }

  readAttempt(hgSessionId, evidenceId) {
    return readJsonIfExists(this.attemptPath(hgSessionId, evidenceId));
  }

  readIndex(hgSessionId) {
    return readJsonIfExists(this.indexPath(hgSessionId));
  }

  listAttemptIds(hgSessionId) {
    const attemptsDir = path.join(this.sessionDir(hgSessionId), 'attempts');
    if (!fs.existsSync(attemptsDir)) return [];
    return fs.readdirSync(attemptsDir)
      .filter((name) => name.endsWith('.json'))
      .map((name) => name.slice(0, -5));
  }

  deleteSession(hgSessionId) {
    const dir = this.sessionDir(hgSessionId);
    if (fs.existsSync(dir)) {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  }

  _indexAttempt(hgSessionId, evidenceId, correlation) {
    const indexPath = this.indexPath(hgSessionId);
    const current = readJsonIfExists(indexPath) ?? {
      schema: INDEX_SCHEMA,
      hg_session_id: hgSessionId,
      attempt_ids: [],
      rounds: {},
      semantic: {
        by_dimension: {},
        hard_findings: [],
        soft_findings: [],
        residual_soft: [],
        multi_candidate_inferences: [],
        exhausted_hard_loops: [],
        successful_correction_chains: [],
        evaluator_failures: [],
        evaluation_chains: {},
      },
    };
    if (!current.semantic) {
      current.semantic = {
        by_dimension: {},
        hard_findings: [],
        soft_findings: [],
        residual_soft: [],
        multi_candidate_inferences: [],
        exhausted_hard_loops: [],
        successful_correction_chains: [],
        evaluator_failures: [],
        evaluation_chains: {},
      };
    }
    if (!current.attempt_ids.includes(evidenceId)) {
      current.attempt_ids.push(evidenceId);
    }
    const roundId = correlation?.hg_round_id;
    if (roundId) {
      const key = String(roundId);
      const roundAttempts = new Set(current.rounds[key] ?? []);
      roundAttempts.add(evidenceId);
      current.rounds[key] = [...roundAttempts];
    }
    current.updated_at = new Date().toISOString();
    writeJsonAtomic(indexPath, current);
  }

  _pushUnique(list, value) {
    if (!value || list.includes(value)) return;
    list.push(value);
  }

  _indexSemanticDecision(hgSessionId, evidenceId, attempt) {
    const decision = attempt?.decision ?? {};
    const correlation = attempt?.correlation ?? {};
    const inferenceId = correlation.inference_id;
    const semantic = decision.semantic_evaluation;
    const outcome = String(decision.outcome ?? '');
    const indexPath = this.indexPath(hgSessionId);
    const current = readJsonIfExists(indexPath);
    if (!current) return;
    if (!current.semantic) {
      current.semantic = {
        by_dimension: {},
        hard_findings: [],
        soft_findings: [],
        residual_soft: [],
        multi_candidate_inferences: [],
        exhausted_hard_loops: [],
        successful_correction_chains: [],
        evaluator_failures: [],
        evaluation_chains: {},
      };
    }
    const sem = current.semantic;

    if (inferenceId) {
      const chainKey = String(inferenceId);
      const chain = new Set(sem.evaluation_chains[chainKey] ?? []);
      chain.add(evidenceId);
      sem.evaluation_chains[chainKey] = [...chain];
    }

    if (outcome === 'semantic_evaluator_failed') {
      this._pushUnique(sem.evaluator_failures, evidenceId);
    }
    if (decision.terminal_disposition === 'hard_exhausted') {
      if (inferenceId) this._pushUnique(sem.exhausted_hard_loops, inferenceId);
    }
    if (outcome === 'accepted' && semantic?.result) {
      if (inferenceId) this._pushUnique(sem.successful_correction_chains, inferenceId);
    }
    if (Array.isArray(decision.residual_soft_concerns) && decision.residual_soft_concerns.length) {
      this._pushUnique(sem.residual_soft, evidenceId);
    }

    const evalResult = semantic?.result ?? semantic;
    const findings = Array.isArray(evalResult?.findings) ? evalResult.findings : [];
    for (const finding of findings) {
      const dimension = String(finding?.dimension ?? '').trim();
      if (!dimension) continue;
      const bucket = sem.by_dimension[dimension] ?? [];
      this._pushUnique(bucket, evidenceId);
      sem.by_dimension[dimension] = bucket;
      if (finding.severity === 'hard') {
        this._pushUnique(sem.hard_findings, evidenceId);
      } else if (finding.severity === 'soft') {
        this._pushUnique(sem.soft_findings, evidenceId);
      }
    }

    if (inferenceId && sem.evaluation_chains[inferenceId]?.length > 2) {
      this._pushUnique(sem.multi_candidate_inferences, inferenceId);
    }

    current.updated_at = new Date().toISOString();
    writeJsonAtomic(indexPath, current);
  }
}
