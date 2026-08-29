import fs from 'node:fs';
import path from 'node:path';

import { ATTEMPT_SCHEMA, INDEX_SCHEMA, NI_FORENSICS_CONTRACT, PLOT_COGNITION_FORENSICS_INDEX_CONTRACT } from './config.mjs';

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

function emptySemanticIndex() {
  return {
    by_dimension: {},
    hard_findings: [],
    soft_findings: [],
    residual_soft: [],
    multi_candidate_inferences: [],
    exhausted_hard_loops: [],
    successful_correction_chains: [],
    evaluator_failures: [],
    evaluation_chains: {},
    qa_by_target_role: {},
    qa_pass_chains: {},
  };
}

function emptyNiIndex() {
  return {
    evidence_contract: NI_FORENSICS_CONTRACT,
    by_round: {},
    by_commit: {},
    by_tag: {},
  };
}

function emptyPlotCognitionIndex() {
  return {
    index_contract: PLOT_COGNITION_FORENSICS_INDEX_CONTRACT,
    by_round: {},
    by_commit: {},
    by_inference_kind: {},
    by_scope: {},
    by_candidate: {},
  };
}

function emptyIndex(hgSessionId) {
  return {
    schema: INDEX_SCHEMA,
    hg_session_id: hgSessionId,
    attempt_ids: [],
    rounds: {},
    participation_by_round: {},
    semantic: emptySemanticIndex(),
    ni: emptyNiIndex(),
    plot_cognition: emptyPlotCognitionIndex(),
  };
}

function mergeDecision(currentDecision, patchDecision) {
  const next = {
    ...(currentDecision ?? {}),
    ...(patchDecision ?? {}),
  };
  const nestedKeys = [
    'director',
    'character_orientation',
    'storyteller_orientation',
    'librarian_mediation',
    'storyteller_advisory',
    'librarian_proposal',
  ];
  for (const key of nestedKeys) {
    if (patchDecision?.[key] || currentDecision?.[key]) {
      next[key] = {
        ...(currentDecision?.[key] ?? {}),
        ...(patchDecision?.[key] ?? {}),
      };
    }
  }
  if (patchDecision?.semantic_qa !== undefined) {
    next.semantic_qa = patchDecision.semantic_qa;
  }
  return next;
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
    delete payload.semantic_qa;
    writeJsonAtomic(this.attemptPath(hgSessionId, evidenceId), payload);
    this._indexAttempt(hgSessionId, evidenceId, attempt.correlation);
    if (attempt.correlation?.role === 'participation') {
      this._indexParticipation(hgSessionId, evidenceId, attempt.correlation);
    }
    if (attempt.evidence_contract === NI_FORENSICS_CONTRACT) {
      this._indexNi(hgSessionId, evidenceId, attempt);
    }
    if (this._isPlotCognitionInference(attempt)) {
      this._indexPlotCognition(hgSessionId, evidenceId, attempt);
    }
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
      decision: mergeDecision(current.decision, patch.decision),
      associations: {
        ...(current.associations ?? {}),
        ...(patch.associations ?? {}),
      },
      updated_at: new Date().toISOString(),
    };
    delete next.semantic_qa;
    writeJsonAtomic(filePath, next);
    this._indexSemanticDecision(hgSessionId, evidenceId, next);
    this._indexSemanticQa(hgSessionId, evidenceId, next);
    if (next.evidence_contract === NI_FORENSICS_CONTRACT) {
      this._indexNi(hgSessionId, evidenceId, next);
    }
    if (this._isPlotCognitionInference(next)) {
      this._indexPlotCognition(hgSessionId, evidenceId, next);
    }
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

  /**
   * Rebuild derived semantic navigation indexes from authoritative attempts.
   */
  rebuildSemanticNavigationIndexes(hgSessionId) {
    const index = readJsonIfExists(this.indexPath(hgSessionId)) ?? emptyIndex(hgSessionId);
    index.semantic = emptySemanticIndex();
    index.participation_by_round = {};
    index.ni = emptyNiIndex();
    index.plot_cognition = emptyPlotCognitionIndex();
    for (const evidenceId of index.attempt_ids ?? []) {
      const attempt = this.readAttempt(hgSessionId, evidenceId);
      if (!attempt) continue;
      if (attempt.correlation?.role === 'participation') {
        this._indexParticipation(hgSessionId, evidenceId, attempt.correlation, index);
        continue;
      }
      this._indexSemanticDecision(hgSessionId, evidenceId, attempt, index);
      this._indexSemanticQa(hgSessionId, evidenceId, attempt, index);
      if (attempt.evidence_contract === NI_FORENSICS_CONTRACT) {
        this._indexNi(hgSessionId, evidenceId, attempt, index);
      }
      if (this._isPlotCognitionInference(attempt)) {
        this._indexPlotCognition(hgSessionId, evidenceId, attempt, index);
      }
    }
    index.updated_at = new Date().toISOString();
    writeJsonAtomic(this.indexPath(hgSessionId), index);
    return index;
  }

  _indexAttempt(hgSessionId, evidenceId, correlation, indexOverride = null) {
    const indexPath = this.indexPath(hgSessionId);
    const current = indexOverride ?? readJsonIfExists(indexPath) ?? emptyIndex(hgSessionId);
    if (!current.semantic) {
      current.semantic = emptySemanticIndex();
    }
    if (!current.participation_by_round) {
      current.participation_by_round = {};
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
    if (!indexOverride) {
      writeJsonAtomic(indexPath, current);
    }
  }

  _indexParticipation(hgSessionId, evidenceId, correlation, indexOverride = null) {
    const roundId = correlation?.hg_round_id;
    if (!roundId) return;
    const indexPath = this.indexPath(hgSessionId);
    const current = indexOverride ?? readJsonIfExists(indexPath);
    if (!current) return;
    if (!current.participation_by_round) {
      current.participation_by_round = {};
    }
    const key = String(roundId);
    const bucket = current.participation_by_round[key] ?? [];
    this._pushUnique(bucket, evidenceId);
    current.participation_by_round[key] = bucket;
    current.updated_at = new Date().toISOString();
    if (!indexOverride) {
      writeJsonAtomic(indexPath, current);
    }
  }

  _pushUnique(list, value) {
    if (!value || list.includes(value)) return;
    list.push(value);
  }

  _indexSemanticDecision(hgSessionId, evidenceId, attempt, indexOverride = null) {
    const decision = attempt?.decision ?? {};
    const correlation = attempt?.correlation ?? {};
    const inferenceId = correlation.inference_id;
    const semantic = decision.semantic_evaluation;
    const outcome = String(decision.outcome ?? '');
    const indexPath = this.indexPath(hgSessionId);
    const current = indexOverride ?? readJsonIfExists(indexPath);
    if (!current) return;
    if (!current.semantic) {
      current.semantic = emptySemanticIndex();
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
    if (!indexOverride) {
      writeJsonAtomic(indexPath, current);
    }
  }

  _indexSemanticQa(hgSessionId, evidenceId, attempt, indexOverride = null) {
    const semanticQa = attempt?.decision?.semantic_qa;
    if (!semanticQa) return;

    const correlation = attempt?.correlation ?? {};
    const inferenceId = correlation.inference_id;
    const indexPath = this.indexPath(hgSessionId);
    const current = indexOverride ?? readJsonIfExists(indexPath);
    if (!current?.semantic) return;

    const targetRole = String(semanticQa.evaluation_target_role ?? '').trim();
    if (!targetRole) return;

    if (!current.semantic.qa_by_target_role) {
      current.semantic.qa_by_target_role = {};
    }
    const bucket = current.semantic.qa_by_target_role[targetRole] ?? [];
    this._pushUnique(bucket, evidenceId);
    current.semantic.qa_by_target_role[targetRole] = bucket;

    if (!current.semantic.qa_pass_chains) {
      current.semantic.qa_pass_chains = {};
    }
    if (inferenceId && semanticQa.evaluation_pass_id) {
      const chainKey = String(inferenceId);
      const chain = [...(current.semantic.qa_pass_chains[chainKey] ?? [])];
      const entry = {
        candidate_evidence_id: evidenceId,
        evaluator_evidence_id: semanticQa.evaluator_evidence_id ?? null,
        evaluation_pass_id: semanticQa.evaluation_pass_id,
        policy_action: semanticQa.policy_action ?? null,
      };
      const existingIndex = chain.findIndex(
        (item) => item.evaluation_pass_id === entry.evaluation_pass_id,
      );
      if (existingIndex >= 0) {
        chain[existingIndex] = entry;
      } else {
        chain.push(entry);
      }
      chain.sort((left, right) => String(left.evaluation_pass_id)
        .localeCompare(String(right.evaluation_pass_id)));
      current.semantic.qa_pass_chains[chainKey] = chain;
    }

    if (semanticQa.infrastructure_failure) {
      this._pushUnique(current.semantic.evaluator_failures, evidenceId);
    }

    const evalResult = semanticQa.result ?? {};
    const findings = Array.isArray(evalResult.findings) ? evalResult.findings : [];
    for (const finding of findings) {
      const dimension = String(finding?.dimension ?? '').trim();
      if (!dimension) continue;
      const dimBucket = current.semantic.by_dimension[dimension] ?? [];
      this._pushUnique(dimBucket, evidenceId);
      current.semantic.by_dimension[dimension] = dimBucket;
      if (finding.severity === 'hard') {
        this._pushUnique(current.semantic.hard_findings, evidenceId);
      } else if (finding.severity === 'soft') {
        this._pushUnique(current.semantic.soft_findings, evidenceId);
      }
    }

    current.updated_at = new Date().toISOString();
    if (!indexOverride) {
      writeJsonAtomic(indexPath, current);
    }
  }

  indexTagForensicScope(hgSessionId, tagId, forensicScope) {
    const indexPath = this.indexPath(hgSessionId);
    const current = readJsonIfExists(indexPath) ?? emptyIndex(hgSessionId);
    if (!current.ni) current.ni = emptyNiIndex();
    current.ni.by_tag = {
      ...(current.ni.by_tag ?? {}),
      [String(tagId)]: forensicScope,
    };
    current.updated_at = new Date().toISOString();
    writeJsonAtomic(indexPath, current);
  }

  _indexNi(hgSessionId, evidenceId, attempt, indexOverride = null) {
    const correlation = attempt?.correlation ?? {};
    const inferenceKind = correlation.inference_kind;
    const parentInferenceId = correlation.parent_inference_id ?? correlation.inference_id;
    const roundId = correlation.hg_round_id;
    const commitId = correlation.domain_commit_id
      ?? attempt?.associations?.domain_commit_id
      ?? attempt?.decision?.commit?.domain_commit_id
      ?? attempt?.decision?.librarian_proposal?.batch_id;
    const indexPath = this.indexPath(hgSessionId);
    const current = indexOverride ?? readJsonIfExists(indexPath) ?? emptyIndex(hgSessionId);
    if (!current.ni) current.ni = emptyNiIndex();
    const ni = current.ni;

    if (roundId && parentInferenceId && inferenceKind) {
      const roundKey = String(roundId);
      const parentKey = String(parentInferenceId);
      ni.by_round[roundKey] = {
        ...(ni.by_round[roundKey] ?? {}),
        [parentKey]: {
          ...(ni.by_round[roundKey]?.[parentKey] ?? {}),
          [inferenceKind]: evidenceId,
        },
      };
    }

    const proposalCommitId = attempt?.associations?.domain_commit_id
      ?? attempt?.decision?.librarian_proposal?.batch_id;
    if (inferenceKind === 'librarian_proposal' && proposalCommitId) {
      ni.by_commit = {
        ...(ni.by_commit ?? {}),
        [String(proposalCommitId)]: {
          ...(ni.by_commit?.[String(proposalCommitId)] ?? {}),
          proposal_evidence_id: evidenceId,
          domain_commit_id: correlation.domain_commit_id ?? null,
        },
      };
    }
    if (commitId && inferenceKind === 'character_move' && attempt?.decision?.commit?.committed) {
      ni.by_commit = {
        ...(ni.by_commit ?? {}),
        [String(correlation.domain_commit_id ?? commitId)]: {
          ...(ni.by_commit?.[String(correlation.domain_commit_id ?? commitId)] ?? {}),
          move_evidence_id: evidenceId,
        },
      };
    }

    current.updated_at = new Date().toISOString();
    if (!indexOverride) {
      writeJsonAtomic(indexPath, current);
    }
  }

  _isPlotCognitionInference(attempt) {
    const kind = String(attempt?.correlation?.inference_kind ?? '');
    return kind.startsWith('plot_cognition') || kind === 'character_advisory_generation';
  }

  _indexPlotCognition(hgSessionId, evidenceId, attempt, indexOverride = null) {
    const correlation = attempt?.correlation ?? {};
    const associations = attempt?.associations ?? {};
    const inferenceKind = correlation.inference_kind;
    const roundId = correlation.hg_round_id;
    const commitId = correlation.domain_commit_id ?? associations.domain_commit_id;
    const scopeId = associations.plot_cognition_scope_id ?? correlation.plot_cognition_scope_id;
    const candidateId = associations.candidate_id ?? correlation.candidate_id;
    const indexPath = this.indexPath(hgSessionId);
    const current = indexOverride ?? readJsonIfExists(indexPath) ?? emptyIndex(hgSessionId);
    if (!current.plot_cognition) current.plot_cognition = emptyPlotCognitionIndex();
    const pc = current.plot_cognition;

    if (inferenceKind) {
      const kindKey = String(inferenceKind);
      const bucket = pc.by_inference_kind[kindKey] ?? [];
      this._pushUnique(bucket, evidenceId);
      pc.by_inference_kind[kindKey] = bucket;
    }
    if (roundId) {
      const roundKey = String(roundId);
      const bucket = pc.by_round[roundKey] ?? [];
      this._pushUnique(bucket, evidenceId);
      pc.by_round[roundKey] = bucket;
    }
    if (commitId) {
      const commitKey = String(commitId);
      const bucket = pc.by_commit[commitKey] ?? [];
      this._pushUnique(bucket, evidenceId);
      pc.by_commit[commitKey] = bucket;
    }
    if (scopeId) {
      const scopeKey = String(scopeId);
      const bucket = pc.by_scope[scopeKey] ?? [];
      this._pushUnique(bucket, evidenceId);
      pc.by_scope[scopeKey] = bucket;
    }
    if (candidateId) {
      const candidateKey = String(candidateId);
      const bucket = pc.by_candidate[candidateKey] ?? [];
      this._pushUnique(bucket, evidenceId);
      pc.by_candidate[candidateKey] = bucket;
    }

    current.updated_at = new Date().toISOString();
    if (!indexOverride) {
      writeJsonAtomic(indexPath, current);
    }
  }
}
