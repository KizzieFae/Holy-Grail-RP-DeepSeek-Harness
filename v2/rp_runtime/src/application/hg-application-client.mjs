import { detectForcedSpeaker } from './detect-forced-speaker.mjs';
import { deepseekInferenceProfile } from '../lib/inference-profile.mjs';
import { HolyGrailRuntimeSupervisor } from '../runtime-supervisor/supervisor.mjs';

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
    this.transcript = [];
    this.lastSpeaker = null;
    this.status = 'idle';
    this.lastError = null;
    this.roundInProgress = false;
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

  async createSession({ cast = DEFAULT_CAST, location = 'Workshop', hgSessionId } = {}) {
    this._requireReady();
    const api = this.orchestrator._domainClient();
    const created = await api.createSession({
      cast,
      location,
      hg_session_id: hgSessionId,
    });
    this.activeSessionId = created.hg_session_id;
    this.activeCast = [...(created.present_characters ?? cast)];
    this.transcript = [];
    this.lastSpeaker = null;
    return this._sessionView(created);
  }

  async openSession(hgSessionId) {
    this._requireReady();
    const api = this.orchestrator._domainClient();
    const opened = await api.openSession(hgSessionId);
    this.activeSessionId = opened.hg_session_id;
    this.activeCast = [...(opened.present_characters ?? DEFAULT_CAST)];
    this.transcript = [];
    this.lastSpeaker = null;
    return this._sessionView(opened);
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
      });
    }

    this.transcript.push({
      role: 'user',
      content: userMessage,
      speaker: input.userName ?? 'Player',
      forced_designation: forcedDesignation,
    });

    this.roundInProgress = true;
    this.lastError = null;
    this.status = 'round_in_progress';

    try {
      const roundOptions = {
        session: { mode: 'open', hg_session_id: this.activeSessionId },
        forcedDesignation,
        ...this._resolveInferenceOptions(input),
      };
      const roundResult = await this.orchestrator.runRound(roundOptions);
      const presentation = presentationFromRound(roundResult);

      if (presentation) {
        this.transcript.push({
          role: 'assistant',
          content: presentation,
          speaker: roundResult.selected_character_id ?? 'Narrator',
          presentation_failed: Boolean(roundResult.presentation_failed),
        });
      }

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
    };
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

  _resolveInferenceOptions(input) {
    if (input.mockDirectorResponses || input.mockCharacterTurnResponses) {
      return {
        mockDirectorResponses: input.mockDirectorResponses,
        mockCharacterTurnResponses: input.mockCharacterTurnResponses,
        mockNarratorTurnResponses: input.mockNarratorTurnResponses,
        liveMaxAttempts: input.liveMaxAttempts,
      };
    }

    if (input.inferenceMode === 'mock' || this.options.inferenceMode === 'mock') {
      return {
        mockDirectorResponses: input.mockDirectorResponses ?? [
          JSON.stringify({
            next_actor: this.activeCast[0] ?? 'Alice',
            end_round: false,
            reason: 'Character should respond.',
            environment_event: '',
            tension_shift: '',
          }),
          JSON.stringify({
            next_actor: this.activeCast[0] ?? 'Alice',
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
      };
    }

    const liveProfile = deepseekInferenceProfile({
      reasoningEffort: input.reasoningEffort ?? 'low',
      maxTokens: input.maxTokens ?? 768,
    });
    return {
      roleProfiles: input.roleProfiles ?? {
        director: liveProfile,
        character: liveProfile,
        narrator: deepseekInferenceProfile({ reasoningEffort: 'off', maxTokens: 384 }),
      },
      liveMaxAttempts: input.liveMaxAttempts ?? 5,
    };
  }
}

export async function startHolyGrailApplication(options = {}) {
  const client = new HolyGrailApplicationClient(options);
  const ready = await client.start();
  return { client, ready };
}
