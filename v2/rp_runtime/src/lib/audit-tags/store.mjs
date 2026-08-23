import fs from 'node:fs';
import path from 'node:path';

import { INDEX_SCHEMA, TAG_SCHEMA } from './config.mjs';

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
 * Low-level HG-native human audit-tag persistence (observational only).
 */
export class AuditTagStore {
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

  tagPath(hgSessionId, tagId) {
    return path.join(this.sessionDir(hgSessionId), 'tags', `${tagId}.json`);
  }

  readIndex(hgSessionId) {
    return readJsonIfExists(this.indexPath(hgSessionId));
  }

  readTag(hgSessionId, tagId) {
    return readJsonIfExists(this.tagPath(hgSessionId, tagId));
  }

  listTagIds(hgSessionId) {
    const index = this.readIndex(hgSessionId);
    return [...(index?.tag_ids ?? [])];
  }

  listTags(hgSessionId) {
    return this.listTagIds(hgSessionId)
      .map((tagId) => this.readTag(hgSessionId, tagId))
      .filter(Boolean)
      .sort((a, b) => (a.tag_index ?? 0) - (b.tag_index ?? 0));
  }

  /**
   * @param {string} hgSessionId
   * @param {object} tag
   * @returns {{ tag: object, created: boolean }}
   */
  createTag(hgSessionId, tag) {
    const entryId = String(tag.anchor.entry_id);
    const index = this._readOrInitIndex(hgSessionId);
    const existingTagId = index.tags_by_entry_id?.[entryId];
    if (existingTagId) {
      const existing = this.readTag(hgSessionId, existingTagId);
      if (existing) {
        return { tag: existing, created: false };
      }
    }

    const tagId = String(tag.tag_id);
    const payload = {
      schema: TAG_SCHEMA,
      ...tag,
      created_at: tag.created_at ?? new Date().toISOString(),
      comment: null,
      comment_updated_at: null,
    };
    writeJsonAtomic(this.tagPath(hgSessionId, tagId), payload);

    if (!index.tag_ids.includes(tagId)) {
      index.tag_ids.push(tagId);
    }
    index.tags_by_entry_id = {
      ...(index.tags_by_entry_id ?? {}),
      [entryId]: tagId,
    };
    index.updated_at = new Date().toISOString();
    writeJsonAtomic(this.indexPath(hgSessionId), index);

    return { tag: payload, created: true };
  }

  /**
   * @param {string} hgSessionId
   * @param {string} tagId
   * @param {string|null} comment
   */
  updateComment(hgSessionId, tagId, comment) {
    const filePath = this.tagPath(hgSessionId, tagId);
    const current = readJsonIfExists(filePath);
    if (!current) return null;
    const nextComment = comment === undefined ? current.comment : comment;
    const normalized = nextComment === null || nextComment === ''
      ? null
      : String(nextComment);
    const next = {
      ...current,
      comment: normalized,
      comment_updated_at: new Date().toISOString(),
    };
    writeJsonAtomic(filePath, next);
    return next;
  }

  deleteTag(hgSessionId, tagId) {
    const index = this.readIndex(hgSessionId);
    if (!index) return false;
    const tag = this.readTag(hgSessionId, tagId);
    if (!tag) return false;

    const entryId = String(tag.anchor?.entry_id ?? '');
    const tagPath = this.tagPath(hgSessionId, tagId);
    if (fs.existsSync(tagPath)) {
      fs.unlinkSync(tagPath);
    }

    index.tag_ids = (index.tag_ids ?? []).filter((id) => id !== tagId);
    if (entryId && index.tags_by_entry_id?.[entryId] === tagId) {
      const nextMap = { ...(index.tags_by_entry_id ?? {}) };
      delete nextMap[entryId];
      index.tags_by_entry_id = nextMap;
    }
    index.updated_at = new Date().toISOString();
    writeJsonAtomic(this.indexPath(hgSessionId), index);
    return true;
  }

  _readOrInitIndex(hgSessionId) {
    const current = this.readIndex(hgSessionId) ?? {
      schema: INDEX_SCHEMA,
      hg_session_id: hgSessionId,
      next_tag_index: 0,
      tag_ids: [],
      tags_by_entry_id: {},
    };
    ensureDir(this.sessionDir(hgSessionId));
    ensureDir(path.join(this.sessionDir(hgSessionId), 'tags'));
    return current;
  }

  allocateTagIndex(hgSessionId) {
    const index = this._readOrInitIndex(hgSessionId);
    const tagIndex = Number(index.next_tag_index ?? 0);
    index.next_tag_index = tagIndex + 1;
    writeJsonAtomic(this.indexPath(hgSessionId), index);
    return tagIndex;
  }
}
