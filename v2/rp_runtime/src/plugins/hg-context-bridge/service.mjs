import { Service } from '@deepseek-ai/cordis';

/**
 * Sole permanent bridge from authoritative Holy Grail prompt manifests to
 * scoped DSH model-visible context for one ephemeral inference.
 *
 * Transports already-decided Python projections; does not interpret domain
 * semantics, ordering policy, or authority classes.
 */
export default class HgContextBridge extends Service {
  static name = 'hgContextBridge';

  constructor(ctx) {
    super(ctx, HgContextBridge.name);
  }

  /**
   * Register one manifest's contributions on the target ephemeral inference agent.
   *
   * @param {object} options
   * @param {object} options.agent - ephemeral DSH inference agent
   * @param {object|null|undefined} options.manifest - PromptContributionManifest from Domain API
   * @returns {{
   *   dispose: () => void,
   *   manifestId: string|null,
   *   contributionIds: string[],
   *   correlation: object,
   * }}
   */
  registerManifest({ agent, manifest }) {
    const contributions = manifest?.contributions ?? [];
    const disposers = [];
    const contributionIds = [];

    for (const contribution of contributions) {
      const contributionId = String(contribution.contribution_id);
      contributionIds.push(contributionId);
      const dispose = agent.ctx.systemPrompt.context({
        name: contributionId,
        order: Number(contribution.priority ?? 0),
        text: String(contribution.content ?? ''),
      });
      disposers.push(dispose);
    }

    return {
      manifestId: manifest?.manifest_id ?? null,
      contributionIds,
      correlation: {
        manifest_id: manifest?.manifest_id ?? null,
        inference_id: manifest?.inference_id ?? null,
        role: manifest?.role ?? null,
        character_id: manifest?.character_id ?? null,
        hg_scene_id: manifest?.hg_scene_id ?? null,
        hg_round_id: manifest?.hg_round_id ?? null,
        turn_index: manifest?.turn_index ?? null,
        attempt_index: manifest?.attempt_index ?? null,
        contribution_ids: contributionIds,
      },
      dispose: () => {
        for (const dispose of disposers) dispose();
      },
    };
  }
}
