import contractJson from '../../../contracts/inference/hg_librarian_mediation_result_v1.inference-contract.json' with { type: 'json' };

import { LIBRARIAN_MEDIATION_RESULT_SCHEMA } from './librarian-mediation-envelope.mjs';

export const LIBRARIAN_MEDIATION_INFERENCE_CONTRACT = contractJson;

function renderFieldSpecs(fieldSpecs = {}) {
  const lines = [];
  for (const [fieldName, spec] of Object.entries(fieldSpecs)) {
    if (spec.type === 'array') {
      lines.push(`- ${fieldName}: array`);
      for (const [itemField, itemSpec] of Object.entries(spec.item_fields ?? {})) {
        const req = itemSpec.required ? 'required' : 'optional';
        let extra = '';
        if (itemSpec.type === 'enum') extra = ` one of ${JSON.stringify(itemSpec.values)}`;
        if (itemSpec.type === 'positive_integer') extra = ' positive integer';
        if (itemSpec.catalog_only) extra = ' catalog source_id only';
        lines.push(`  - ${itemField} (${req})${extra}`);
      }
    } else {
      const req = spec.required ? 'required' : 'optional';
      lines.push(`- ${fieldName} (${req})`);
    }
  }
  return lines;
}

export function buildLibrarianMediationContractSpec({
  sampleSourceId = 'lmi:cand:example-source',
} = {}) {
  const example = JSON.parse(JSON.stringify(contractJson.minimal_valid_example));
  if (example.selected_items?.[0]) {
    example.selected_items[0].source_id = sampleSourceId;
  }
  if (example.synthesis_entries?.[0]) {
    example.synthesis_entries[0].source_ids = [sampleSourceId];
  }
  return {
    schema: LIBRARIAN_MEDIATION_RESULT_SCHEMA,
    contract: contractJson,
    minimal_example: example,
    forbidden_aliases: contractJson.forbidden_field_aliases ?? [],
    forbidden_behaviors: contractJson.forbidden_behaviors ?? [],
  };
}

export function librarianMediationContractPromptLines({
  sampleSourceId = 'lmi:cand:example-source',
} = {}) {
  const spec = buildLibrarianMediationContractSpec({ sampleSourceId });
  const requiredTop = (contractJson.required_top_level ?? []).join(', ');
  const aliasLines = (spec.forbidden_aliases ?? []).map(
    (alias) => `- ${alias.path} — use ${alias.use_instead} instead`,
  );
  const behaviorLines = (spec.forbidden_behaviors ?? []).map((rule) => `- ${rule}`);
  return [
    `Required output contract for schema ${spec.schema}:`,
    '',
    'Top-level object MUST include:',
    `- schema: exact string "${spec.schema}"`,
    `- required fields: ${requiredTop}`,
    '',
    'Field specifications:',
    ...renderFieldSpecs(contractJson.field_specs ?? {}),
    '',
    'Forbidden field aliases (do NOT use):',
    ...aliasLines,
    '',
    'Forbidden behaviors:',
    ...behaviorLines,
    '',
    'Minimal valid example (replace source_id with catalog values):',
    JSON.stringify(spec.minimal_example, null, 2),
  ];
}

export function contractRequiredSelectedItemFields() {
  const itemFields = contractJson.field_specs?.selected_items?.item_fields ?? {};
  return Object.entries(itemFields)
    .filter(([, spec]) => spec.required)
    .map(([name]) => name);
}
