import crypto from 'node:crypto';

import { auditTagsRoot } from './config.mjs';
import { enrichTagWithForensicScope, resolveTagForensicScope } from './forensic-scope.mjs';
import { buildAnchorFromHistoryEntry, findHistoryEntryById } from './resolve-anchor.mjs';
import { AuditTagStore } from './store.mjs';
import { createExecutionEvidenceRecorder } from '../execution-evidence/recorder.mjs';

export class AuditTagService {
  /**
   * @param {{ root?: string, env?: NodeJS.ProcessEnv, evidenceRecorder?: object }} [options]
   */
  constructor(options = {}) {
    const root = options.root ?? auditTagsRoot(options.env);
    this.store = new AuditTagStore(root);
    this.evidenceRecorder = options.evidenceRecorder
      ?? createExecutionEvidenceRecorder({ env: options.env });
  }

  /**
   * @param {object} params
   * @param {string} params.hgSessionId
   * @param {string} params.entryId
   * @param {() => Promise<{ entries?: object[] }>} params.getHistory
   * @param {{ surface?: string, persona?: string }} [params.createdBy]
   */
  async createTag({ hgSessionId, entryId, getHistory, createdBy }) {
    const history = await getHistory();
    const entries = history.entries ?? [];
    const entry = findHistoryEntryById(entries, entryId);
    if (!entry) {
      throw new Error(`unknown transcript entry_id: ${entryId}`);
    }

    const existingIndex = this.store.readIndex(hgSessionId);
    const existingTagId = existingIndex?.tags_by_entry_id?.[String(entryId)];
    if (existingTagId) {
      const existing = this.store.readTag(hgSessionId, existingTagId);
      if (existing) {
        return { tag: existing, created: false };
      }
    }

    const tagIndex = this.store.allocateTagIndex(hgSessionId);
    const tagId = crypto.randomUUID();
    const anchor = buildAnchorFromHistoryEntry(entry);
    const forensicScope = resolveTagForensicScope({
      hgSessionId,
      anchor,
      evidenceRecorder: this.evidenceRecorder,
    });
    const tag = enrichTagWithForensicScope({
      tag_id: tagId,
      tag_index: tagIndex,
      hg_session_id: hgSessionId,
      anchor,
      created_by: {
        surface: createdBy?.surface ?? 'api',
        persona: createdBy?.persona ?? 'Player',
      },
    }, forensicScope, this.evidenceRecorder, hgSessionId);

    return this.store.createTag(hgSessionId, tag);
  }

  listTags(hgSessionId) {
    return this.store.listTags(hgSessionId);
  }

  getTag(hgSessionId, tagId) {
    return this.store.readTag(hgSessionId, tagId);
  }

  updateComment(hgSessionId, tagId, comment) {
    const updated = this.store.updateComment(hgSessionId, tagId, comment);
    if (!updated) {
      throw new Error(`unknown audit tag: ${tagId}`);
    }
    return updated;
  }

  deleteTag(hgSessionId, tagId) {
    const removed = this.store.deleteTag(hgSessionId, tagId);
    if (!removed) {
      throw new Error(`unknown audit tag: ${tagId}`);
    }
    return { deleted: true, tag_id: tagId };
  }
}
