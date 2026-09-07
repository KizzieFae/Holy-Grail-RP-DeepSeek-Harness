import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  CATALOG_SCHEMA,
  HARNESS_ANNEX_CATALOG,
  PRIMARY_RUNTIME_CATALOG,
} from '../src/application/llm-call-catalog.mjs';
import { buildGeneratedCatalogRow } from '../src/application/llm-call-catalog-policy.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..', '..', '..');
const catalogPath = path.join(repoRoot, 'docs', 'llm-call-catalog.json');
const charIndexPath = path.join(repoRoot, 'data', 'llm_characterization', 'index.json');

function loadEmpiricalStatus(options = {}) {
  if (!fs.existsSync(charIndexPath)) return {};
  const index = JSON.parse(fs.readFileSync(charIndexPath, 'utf8'));
  const preferredMode = options.preferredInferenceMode ?? 'live';
  const out = {};
  for (const [callId, meta] of Object.entries(index.call_latest ?? {})) {
    if (preferredMode && meta.inference_mode && meta.inference_mode !== preferredMode) {
      continue;
    }
    out[callId] = {
      characterization_status: meta.stability_class ?? 'complete',
      characterization_summary_ref: meta.summary_path ?? null,
      inference_mode: meta.inference_mode ?? null,
    };
  }
  if (preferredMode === 'live' && Object.keys(out).length === 0) {
    return loadEmpiricalStatus({ preferredInferenceMode: null });
  }
  return out;
}

export function generateLlmCallCatalog(options = {}) {
  const settings = { inferenceMode: 'live', roleRouting: 'simple' };
  const empiricalByCall = options.empiricalByCall ?? loadEmpiricalStatus({
    preferredInferenceMode: options.preferredInferenceMode ?? 'live',
  });
  const generatedAt = options.generatedAt ?? new Date().toISOString();
  const anchor = options.repositoryAnchor ?? null;

  const primary_runtime = PRIMARY_RUNTIME_CATALOG.map((entry) => buildGeneratedCatalogRow(
    entry,
    settings,
    {},
    empiricalByCall[entry.call_id] ?? {},
  ));
  const harness_annex = HARNESS_ANNEX_CATALOG.map((entry) => buildGeneratedCatalogRow(
    entry,
    settings,
    {},
    { characterization_status: 'excluded', characterization_summary_ref: null },
  ));

  return {
    schema: CATALOG_SCHEMA,
    generated_at: generatedAt,
    repository_anchor: anchor,
    terminology: {
      canonical_inference_kinds: 26,
      production_utilized_unique_kinds: 24,
      primary_runtime_configuration_rows: primary_runtime.length,
      harness_annex_rows: harness_annex.length,
    },
    policy_authority: 'v2/rp_runtime/src/application/application-settings.mjs',
    metadata_authority: 'v2/rp_runtime/src/application/llm-call-catalog.mjs',
    application_token_quota_policy: {
      enforced: false,
      summary: 'Holy-Grail application maxTokens are globally disabled during the present LLM/prompt-efficiency development period. reference_application_token_quota preserves baseline assignments for later analysis; application_token_quota reflects current enforcement (UNCAPPED). Provider/model-native limits and non-token safeguards still apply.',
    },
    primary_runtime,
    harness_annex,
  };
}

function main() {
  const doc = generateLlmCallCatalog({
    repositoryAnchor: process.env.HG_REPO_ANCHOR ?? null,
  });
  fs.mkdirSync(path.dirname(catalogPath), { recursive: true });
  fs.writeFileSync(catalogPath, `${JSON.stringify(doc, null, 2)}\n`);
  console.log(`Wrote ${catalogPath}`);
}

const isMain = process.argv[1]
  && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
if (isMain) {
  main();
}
