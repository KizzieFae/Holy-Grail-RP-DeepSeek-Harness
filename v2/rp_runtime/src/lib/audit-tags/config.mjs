import path from 'node:path';

import { defaultDataDir } from '../runtime-config.mjs';

export const TAG_SCHEMA = 'hg_audit_tag_v1';
export const INDEX_SCHEMA = 'hg_audit_tags_index_v1';

/**
 * Root directory for session-scoped human audit-tag trees.
 */
export function auditTagsRoot(env = process.env) {
  const explicit = String(env.HG_AUDIT_TAGS_DIR ?? '').trim();
  if (explicit) return path.resolve(explicit);
  return path.join(defaultDataDir(env), 'audit_tags');
}
