import { detectForcedSpeaker } from './detect-forced-speaker.mjs';
import crypto from 'node:crypto';
import {
  buildInferenceOptions,
  defaultRuntimeSettings,
  settingsView,
  validateRuntimeSettings,
  validateSessionSetup,
} from './application-settings.mjs';
import { AuditTagService } from '../lib/audit-tags/service.mjs';
import { agentOptionsFromProfile, mockInferenceProfile } from '../lib/inference-profile.mjs';
import { HolyGrailRuntimeSupervisor } from '../runtime-supervisor/supervisor.mjs';
import { SessionId } from '@deepseek-ai/dsh-session';

const DEFAULT_CAST = ['Alice'];

function classifyFailure(err) {
  const message = err instanceof Error ? err.message : String(err);
  if (/DEEPSEEK|provider|credential|inference/i.test(message)) {
    return { category: 'provider_failure', message };
  }
  if (/validation|reject|domain api|commit/i.test(message)) {
    return { category: 'domain_failure', message };
  }
  if (/health|domain host|unavailable|fetch failed/i.test(message)) {
    return { category: 'runtime_unavailable', message };
  }
  return { category: 'round_failure', message };
}

function presentationFromRound(roundResult) {
  if (roundResult.presentation_text) {
    return roundResult.presentation_text;
  }
  const lastTurn = roundResult.character_turns?.at(-1);
  return lastTurn?.presentation_text ?? '';
}

export class HolyGrailApplicationClient {
  constructor(options = {}) {
    this.options = options;
    this.supervisor = new HolyGrailRuntimeSupervisor({
      ...options,
      runtime: {
        ...(options.runtime ?? {}),
        inference: options.runtime?.inference ?? (
          options.inferenceMode === 'mock' ? {} : { mountDeepSeek: true }
        ),
      },
    });
    this.activeSessionId = null;
    this.activeCast = [...DEFAULT_CAST];
    this.characterFileIds = {};
    this.setupProvenance = null;
    this.memoryScopeId = null;
    this.userPersonaId = 'Player';
    this.runtimeSettings = defaultRuntimeSettings({
      inferenceMode: options.inferenceMode,
    });
    this.transcript = [];
    this.lastSpeaker = null;
    this.status = 'idle';
    this.lastError = null;
    this.roundInProgress = false;
    this.auditTags = new AuditTagService({ env: options.env });
  }

  get orchestrator() {
    return this.supervisor.runtime?.orchestrator ?? null;
  }

  get ready() {
    return this.supervisor.ready;
  }

  getHealth() {
    if (this.roundInProgress) {
      return { ...this.supervisor.getReadyState(), application_status: 'round_in_progress' };
    }
    if (this.lastError) {
      return { ...this.supervisor.getReadyState(), application_status: 'error', last_error: this.lastError };
    }
    return { ...this.supervisor.getReadyState(), application_status: this.status };
  }

  async start() {
    this.status = 'starting';
    this.lastError = null;
    try {
      const ready = await this.supervisor.start();
      this.status = 'ready';
      return ready;
    } catch (err) {
      this.status = 'failed';
      this.lastError = classifyFailure(err);
      throw err;
    }
  }

  async stop() {
    await this.supervisor.stop();
    this.status = 'stopped';
    this.roundInProgress = false;
  }

  async createSession(input = {}) {
    this._requireReady();
    const validation = validateSessionSetup(input);
    if (!validation.valid) {
      throw new Error(validation.errors.join('; '));
    }
    const api = this.orchestrator._domainClient();
    const body = {};
    if (input.characters?.length) {
      body.characters = input.characters;
      if (input.scene_template_id) body.scene_template_id = input.scene_template_id;
      if (input.sceneTemplateId) body.scene_template_id = input.sceneTemplateId;
      if (input.role_assignments) body.role_assignments = input.role_assignments;
      if (input.roleAssignments) body.role_assignments = input.roleAssignments;
      if (input.opening) body.opening = input.opening;
      if (input.location) body.location = input.location;
    } else {
      body.cast = input.cast ?? DEFAULT_CAST;
      body.location = input.location ?? 'Workshop';
    }
    if (input.hgSessionId ?? input.hg_session_id) {
      body.hg_session_id = input.hgSessionId ?? input.hg_session_id;
    }
    if (input.memoryScopeId ?? input.memory_scope_id) {
      body.memory_scope_id = input.memoryScopeId ?? input.memory_scope_id;
    }
    if (input.playerCharacterFileId ?? input.player_character_file_id) {
      body.player_character_file_id =
        input.playerCharacterFileId ?? input.player_character_file_id;
    }
    if (input.userPersonaId ?? input.user_persona_id) {
      body.user_persona_id = input.userPersonaId ?? input.user_persona_id;
    }
    const created = await api.createSession(body);
    this._applySessionPayload(created);
    const openingMode = String(body.opening?.mode ?? '').toLowerCase();
    if (openingMode === 'generated') {
      await this._generateAndPersistOpening({
        ...input,
        mockOpeningResponses: input.mockOpeningResponses,
      });
    } else if (openingMode === 'template') {
      await this._segmentTemplateOpening({
        ...input,
        mockOpeningSegmentationResponses: input.mockOpeningSegmentationResponses,
      });
    }
    await this._refreshTranscript();
    return this._sessionView(created);
  }

  async openSession(hgSessionId) {
    this._requireReady();
    const api = this.orchestrator._domainClient();
    const opened = await api.openSession(hgSessionId);
    this._applySessionPayload(opened);
    await this._refreshTranscript();
    return this._sessionView(opened);
  }

  getRuntimeSettings() {
    return { ...this.runtimeSettings };
  }

  updateRuntimeSettings(patch = {}) {
    const merged = { ...this.runtimeSettings, ...patch };
    const validation = validateRuntimeSettings(merged);
    if (!validation.valid) {
      throw new Error(validation.errors.join('; '));
    }
    this.runtimeSettings = merged;
    return this.getRuntimeSettings();
  }

  getSettingsView() {
    return settingsView(this.runtimeSettings);
  }

  validateSessionSetup(input = {}) {
    return validateSessionSetup(input);
  }

  validateRuntimeSettings(input = {}) {
    return validateRuntimeSettings(input);
  }

  async listCharacters() {
    this._requireReady();
    const api = this.orchestrator._domainClient();
    const payload = await api.listCharacters();
    return payload.characters ?? [];
  }

  async listSceneTemplates() {
    this._requireReady();
    const api = this.orchestrator._domainClient();
    const payload = await api.listSceneTemplates();
    return payload.scene_templates ?? [];
  }

  async listTemplateOpeners(templateId) {
    this._requireReady();
    const api = this.orchestrator._domainClient();
    const payload = await api.listTemplateOpeners(templateId);
    return payload.openers ?? [];
  }

  async generateOpening(input = {}) {
    this._requireReady();
    this._requireActiveSession();
    return this._generateAndPersistOpening(input);
  }

  async getSessionState() {
    this._requireReady();
    this._requireActiveSession();
    const api = this.orchestrator._domainClient();
    return api.getSessionState(this.activeSessionId);
  }

  getTranscript() {
    return [...this.transcript];
  }

  async submitUserTurn(input = {}) {
    this._requireReady();
    this._requireActiveSession();

    const userMessage = String(input.userMessage ?? input.user_message ?? '').trim();
    if (!userMessage) {
      throw new Error('userMessage is required');
    }

    const state = await this.getSessionState();
    const cast = [...(state.present_characters ?? this.activeCast)];
    let forcedDesignation = input.forcedDesignation ?? input.forced_designation ?? null;
    if (!forcedDesignation) {
      forcedDesignation = detectForcedSpeaker(userMessage, {
        participantNames: cast,
        previousParticipantSpeaker: this.lastSpeaker,
        characterFileIds: this.characterFileIds,
      });
    }

    const api = this.orchestrator._domainClient();
    await api.recordUserTurn({
      hg_session_id: this.activeSessionId,
      content: userMessage,
      speaker: input.userName ?? input.user_name ?? this.userPersonaId ?? 'Player',
      forced_designation: forcedDesignation,
    });

    return this._runActiveRound({
      forcedDesignation,
      inferenceInput: input,
    });
  }

  async submitSkipTurn(input = {}) {
    this._requireReady();
    this._requireActiveSession();

    const api = this.orchestrator._domainClient();
    await api.recordPlayerSkip({
      hg_session_id: this.activeSessionId,
      speaker: input.userName ?? input.user_name ?? this.userPersonaId ?? 'Player',
    });

    return this._runActiveRound({
      forcedDesignation: null,
      inferenceInput: input,
    });
  }

  async _runActiveRound({ forcedDesignation, inferenceInput = {} }) {
    const api = this.orchestrator._domainClient();
    this.roundInProgress = true;
    this.lastError = null;
    this.status = 'round_in_progress';

    try {
      const roundOptions = {
        session: { mode: 'open', hg_session_id: this.activeSessionId },
        forcedDesignation,
        ...this._resolveInferenceOptions(inferenceInput),
      };
      const roundResult = await this.orchestrator.runRound(roundOptions);
      await this._recordRoundPresentations(api, roundResult);
      await this._refreshTranscript();
      const presentation = presentationFromRound(roundResult);

      if (roundResult.selected_character_id) {
        this.lastSpeaker = roundResult.selected_character_id;
      }

      this.status = 'ready';
      return {
        session: await this.getSessionState(),
        round: roundResult,
        presentation,
        transcript: this.getTranscript(),
        forced_designation: forcedDesignation,
      };
    } catch (err) {
      const failure = classifyFailure(err);
      this.lastError = failure;
      this.status = 'ready';
      throw Object.assign(err instanceof Error ? err : new Error(String(err)), { failure });
    } finally {
      this.roundInProgress = false;
    }
  }

  _sessionView(payload) {
    return {
      hg_session_id: payload.hg_session_id,
      hg_scene_id: payload.hg_scene_id ?? payload.hg_session_id,
      turn_counter: payload.turn_counter ?? payload.continuity_turn_index ?? 0,
      present_characters: payload.present_characters ?? this.activeCast,
      location: payload.location ?? 'Workshop',
      continuity_version: payload.continuity_version ?? 0,
      committed_move_count: payload.committed_move_count ?? 0,
      setup_provenance: payload.setup_provenance ?? this.setupProvenance,
      character_file_ids: payload.character_file_ids ?? this.characterFileIds,
      memory_scope_id: payload.memory_scope_id ?? this.memoryScopeId,
    };
  }

  _applySessionPayload(payload) {
    this.activeSessionId = payload.hg_session_id;
    this.activeCast = [...(payload.present_characters ?? DEFAULT_CAST)];
    this.characterFileIds = { ...(payload.character_file_ids ?? {}) };
    this.setupProvenance = payload.setup_provenance ?? null;
    this.memoryScopeId = payload.memory_scope_id ?? null;
    this.userPersonaId = this.setupProvenance?.user_persona_id ?? 'Player';
  }

  _requireReady() {
    if (!this.ready || !this.orchestrator) {
      throw new Error('application runtime is not ready');
    }
  }

  _requireActiveSession() {
    if (!this.activeSessionId) {
      throw new Error('no active hg_session_id — create or open a session first');
    }
  }

  async _refreshTranscript() {
    if (!this.activeSessionId) {
      this.transcript = [];
      this.lastSpeaker = null;
      return;
    }
    const api = this.orchestrator._domainClient();
    const history = await api.getSessionHistory(this.activeSessionId);
    this.transcript = [...(history.transcript ?? [])];
    const lastAssistant = [...this.transcript].reverse().find((entry) => entry.role === 'assistant');
    if (lastAssistant?.speaker && lastAssistant.speaker !== 'Narrator') {
      this.lastSpeaker = lastAssistant.speaker;
    }
  }

  async _recordRoundPresentations(api, roundResult) {
    const turns = roundResult.character_turns ?? [];
    if (turns.length) {
      for (const turn of turns) {
        if (!turn.domain_commit_id) continue;
        await api.recordPresentation({
          hg_session_id: this.activeSessionId,
          domain_commit_id: turn.domain_commit_id,
          hg_round_id: roundResult.hg_round_id,
          character_id: turn.character_id,
          presentation_text: turn.presentation_text,
          presentation_failed: Boolean(turn.presentation_failed),
          inference_outcome: turn.inference_outcome,
          narrative_visibility: turn.narrative_visibility ?? null,
        });
      }
      return;
    }
    if (roundResult.domain_commit_id) {
      await api.recordPresentation({
        hg_session_id: this.activeSessionId,
        domain_commit_id: roundResult.domain_commit_id,
        hg_round_id: roundResult.hg_round_id,
        character_id: roundResult.selected_character_id ?? 'Character',
        presentation_text: roundResult.presentation_text,
        presentation_failed: Boolean(roundResult.presentation_failed),
        inference_outcome: roundResult.inference_outcome,
        narrative_visibility: roundResult.narrative_visibility ?? null,
      });
    }
  }

  async _generateAndPersistOpening(input = {}) {
    const api = this.orchestrator._domainClient();
    const history = await api.getSessionHistory(this.activeSessionId);
    const hasOpening = (history.entries ?? []).some((entry) => entry.kind === 'opening');
    if (hasOpening) {
      return { presentation_rendered: true, skipped: true };
    }

    const phaseExecutors = this.supervisor.runtime?.phaseExecutors;
    const trace = this.supervisor.runtime?.traceEmitter;
    if (!phaseExecutors || !trace) {
      throw new Error('opening generation requires DSH phase executors');
    }

    const hgSessionId = this.activeSessionId;
    const hgSceneId = hgSessionId;
    const openingInferenceId = `opening-${crypto.randomUUID()}`;
    const sceneSessionId = SessionId(`hg-opening-${crypto.randomUUID()}`);
    const sceneAgent = this.supervisor.runtime.ctx.agentLoop.create(
      sceneSessionId,
      agentOptionsFromProfile(mockInferenceProfile()),
    );

    const inference = buildInferenceOptions(
      { ...this.runtimeSettings, ...input },
      { inferenceMode: this.options.inferenceMode },
    );
    const modelProfile =
      input.inferenceMode === 'mock' || this.options.inferenceMode === 'mock'
        ? mockInferenceProfile()
        : inference.roleProfiles.opening;

    const openingResult = await phaseExecutors.runOpening({
      api,
      trace,
      sceneAgent,
      sceneSessionId,
      hgSessionId,
      hgSceneId,
      openingInferenceId,
      mockOpeningResponses: input.mockOpeningResponses,
      modelProfile,
      maxAttempts: Number(input.openingMaxAttempts ?? 2),
    });

    if (openingResult.presentation_rendered && openingResult.presentation_text) {
      await api.persistOpening({
        hg_session_id: hgSessionId,
        inference_id: openingResult.inference_id ?? openingInferenceId,
        presentation_text: openingResult.presentation_text,
        presentation_failed: false,
        manifest_id: openingResult.opening_manifest_id,
        narrative_visibility: openingResult.narrative_visibility ?? null,
      });
      await this._refreshTranscript();
    }

    return openingResult;
  }

  async _segmentTemplateOpening(input = {}) {
    const api = this.orchestrator._domainClient();
    const history = await api.getSessionHistory(this.activeSessionId);
    const openingEntry = (history.entries ?? []).find((entry) => entry.kind === 'opening');
    if (!openingEntry) {
      return { segmented: false, skipped: true, reason: 'no template opening entry' };
    }
    if (openingEntry.metadata?.narrative_visibility?.units?.length) {
      return { segmented: true, skipped: true, reason: 'narrative visibility already present' };
    }

    const phaseExecutors = this.supervisor.runtime?.phaseExecutors;
    const trace = this.supervisor.runtime?.traceEmitter;
    if (!phaseExecutors || !trace) {
      throw new Error('template opening segmentation requires DSH phase executors');
    }

    const hgSessionId = this.activeSessionId;
    const hgSceneId = hgSessionId;
    const segmentationInferenceId = `opening-segmentation-${crypto.randomUUID()}`;
    const sceneSessionId = SessionId(`hg-opening-segmentation-${crypto.randomUUID()}`);
    const sceneAgent = this.supervisor.runtime.ctx.agentLoop.create(
      sceneSessionId,
      agentOptionsFromProfile(mockInferenceProfile()),
    );

    const inference = buildInferenceOptions(
      { ...this.runtimeSettings, ...input },
      { inferenceMode: this.options.inferenceMode },
    );
    const modelProfile =
      input.inferenceMode === 'mock' || this.options.inferenceMode === 'mock'
        ? mockInferenceProfile()
        : inference.roleProfiles.opening;

    return phaseExecutors.runOpeningSegmentation({
      api,
      trace,
      sceneAgent,
      sceneSessionId,
      hgSessionId,
      hgSceneId,
      segmentationInferenceId,
      mockOpeningSegmentationResponses: input.mockOpeningSegmentationResponses,
      modelProfile,
      maxAttempts: Number(input.openingSegmentationMaxAttempts ?? 2),
    });
  }

  _resolveInferenceOptions(input) {
    if (input.mockDirectorResponses || input.mockCharacterTurnResponses) {
      return {
        mockDirectorResponses: input.mockDirectorResponses,
        mockCharacterTurnResponses: input.mockCharacterTurnResponses,
        mockNarratorTurnResponses: input.mockNarratorTurnResponses,
        liveMaxAttempts: input.liveMaxAttempts,
      };
    }

    const inference = buildInferenceOptions(
      { ...this.runtimeSettings, ...input },
      { inferenceMode: this.options.inferenceMode ?? input.inferenceMode },
    );

    if (inference.inferenceMode === 'mock') {
      return {
        mockDirectorResponses: input.mockDirectorResponses ?? [
          JSON.stringify({
            next_actor: this._firstAiActor(),
            end_round: false,
            reason: 'Character should respond.',
            environment_event: '',
            tension_shift: '',
          }),
          JSON.stringify({
            next_actor: this._firstAiActor(),
            end_round: true,
            reason: 'Round complete.',
            environment_event: '',
            tension_shift: '',
          }),
        ],
        mockCharacterTurnResponses: input.mockCharacterTurnResponses ?? [[
          JSON.stringify({
            move_schema_version: 2,
            beats: [{ type: 'action', action: 'nods thoughtfully' }],
            motivation: {
              goal: 'acknowledge',
              tactic: 'subtle gesture',
              emotional_driver: 'calm',
              risk_level: 'low',
            },
            semantic_evaluation: { decision: 'no_covered_change' },
          }),
        ]],
        mockNarratorTurnResponses: input.mockNarratorTurnResponses,
        mockOpeningResponses: input.mockOpeningResponses,
      };
    }

    return {
      roleProfiles: inference.roleProfiles,
      liveMaxAttempts: inference.liveMaxAttempts,
    };
  }

  _firstAiActor() {
    const controlModes = this.setupProvenance?.control_modes ?? {};
    const aiActor = this.activeCast.find((name) => controlModes[name] !== 'player');
    return aiActor ?? this.activeCast[0] ?? 'Alice';
  }

  _resolveAuditSessionId(hgSessionId) {
    const resolved = hgSessionId ?? this.activeSessionId;
    if (!resolved) {
      throw new Error('hg_session_id required');
    }
    return resolved;
  }

  async createAuditTag({ hgSessionId, entryId, createdBy } = {}) {
    this._requireReady();
    const sessionId = this._resolveAuditSessionId(hgSessionId);
    if (!entryId) {
      throw new Error('entry_id required');
    }
    if (sessionId !== this.activeSessionId) {
      await this.openSession(sessionId);
    }
    const api = this.orchestrator._domainClient();
    return this.auditTags.createTag({
      hgSessionId: sessionId,
      entryId,
      createdBy,
      getHistory: () => api.getSessionHistory(sessionId),
    });
  }

  listAuditTags(hgSessionId) {
    const sessionId = this._resolveAuditSessionId(hgSessionId);
    return this.auditTags.listTags(sessionId);
  }

  getAuditTag({ hgSessionId, tagId }) {
    const sessionId = this._resolveAuditSessionId(hgSessionId);
    const tag = this.auditTags.getTag(sessionId, tagId);
    if (!tag) {
      throw new Error(`unknown audit tag: ${tagId}`);
    }
    return tag;
  }

  updateAuditTagComment({ hgSessionId, tagId, comment }) {
    const sessionId = this._resolveAuditSessionId(hgSessionId);
    return this.auditTags.updateComment(sessionId, tagId, comment);
  }

  deleteAuditTag({ hgSessionId, tagId }) {
    const sessionId = this._resolveAuditSessionId(hgSessionId);
    return this.auditTags.deleteTag(sessionId, tagId);
  }
}

export async function startHolyGrailApplication(options = {}) {
  const client = new HolyGrailApplicationClient(options);
  const ready = await client.start();
  return { client, ready };
}
