/**
 * Issue #201 LH-0 — arm configuration definitions (LH-A through LH-D).
 */
import { LH0_SCHEMAS } from './issue201-lifecycle-states.mjs';

export const LH0_ARMS = Object.freeze({
  LH_A: 'lh_a',
  LH_B: 'lh_b',
  LH_C: 'lh_c',
  LH_D: 'lh_d',
});

const BASE_A2_OPTIONS = {
  skipPostCommitPlot: true,
  captureActorContextPackages: true,
  uniformProjectionEligible: true,
};

export function buildLh0ArmConfig(arm) {
  const common = {
    schema: LH0_SCHEMAS.ARM_CONFIG,
    arm,
    persistent_cognition_enabled: false,
    projection_lifecycle_enabled: false,
    consumption_lifecycle_enforcer: false,
    skip_character_knowledge_cognition: true,
    sync_storyteller_preamble: false,
    sync_storyteller_post_commit: false,
    narrative_priority_guidance_enabled: false,
    route_trivial_director_through_persistent: false,
    unconditional_director_override: false,
    beat_options: { ...BASE_A2_OPTIONS },
  };

  switch (arm) {
    case LH0_ARMS.LH_A:
      return {
        ...common,
        label: 'a2_primary_only',
        cognition_mechanisms: [],
        authorized_consumers: [],
        fairness: { director_retains_selection: true },
      };
    case LH0_ARMS.LH_B:
      return {
        ...common,
        label: 'a2_plot_scribe',
        persistent_cognition_enabled: true,
        projection_lifecycle_enabled: true,
        consumption_lifecycle_enforcer: true,
        skip_character_knowledge_cognition: false,
        cognition_mechanisms: ['plot_cognition_init', 'plot_cognition_update'],
        preservation_mechanism: 'plot_overlay',
        authorized_consumers: ['character_move', 'director_turn'],
        beat_options: {
          ...BASE_A2_OPTIONS,
          skipPostCommitPlot: false,
          projectionLifecycleEnabled: true,
          skipCharacterKnowledgeCognition: false,
          lh0Arm: LH0_ARMS.LH_B,
        },
        fairness: { director_retains_selection: true },
      };
    case LH0_ARMS.LH_C:
      return {
        ...common,
        label: 'a2_storyteller_persistent',
        persistent_cognition_enabled: true,
        projection_lifecycle_enabled: true,
        consumption_lifecycle_enforcer: true,
        skip_character_knowledge_cognition: false,
        sync_storyteller_preamble: false,
        sync_storyteller_post_commit: false,
        cognition_mechanisms: [
          'persistent_storyteller_agenda',
          'persistent_storyteller_tension',
          'persistent_storyteller_trajectory',
        ],
        preservation_mechanism: 'storyteller_state',
        authorized_consumers: ['director_turn', 'character_move'],
        beat_options: {
          ...BASE_A2_OPTIONS,
          skipPostCommitPlot: true,
          projectionLifecycleEnabled: true,
          skipCharacterKnowledgeCognition: false,
          lh0Arm: LH0_ARMS.LH_C,
        },
        fairness: { director_retains_selection: true },
      };
    case LH0_ARMS.LH_D:
      return {
        ...common,
        label: 'a2_narrative_intel_consolidated',
        persistent_cognition_enabled: true,
        projection_lifecycle_enabled: true,
        consumption_lifecycle_enforcer: true,
        skip_character_knowledge_cognition: false,
        narrative_priority_guidance_enabled: true,
        cognition_mechanisms: ['consolidated_narrative_intelligence'],
        preservation_mechanism: 'consolidated_state',
        authorized_consumers: ['director_turn', 'character_move'],
        beat_options: {
          ...BASE_A2_OPTIONS,
          skipPostCommitPlot: false,
          projectionLifecycleEnabled: true,
          skipCharacterKnowledgeCognition: false,
          lh0Arm: LH0_ARMS.LH_D,
          narrativePriorityGuidanceOnly: true,
        },
        fairness: {
          director_retains_selection: true,
          deterministic_eligibility_first: true,
          guidance_not_dictation: true,
          no_continuity_mutation: true,
          no_unconditional_override: true,
        },
      };
    default:
      throw new Error(`unknown LH-0 arm: ${arm}`);
  }
}

export function buildAllLh0ArmConfigs() {
  return Object.values(LH0_ARMS).map((arm) => buildLh0ArmConfig(arm));
}

export function resolveLh0BeatOptions(armConfig) {
  return {
    ...armConfig.beat_options,
    projectionLifecycleEnabled: armConfig.projection_lifecycle_enabled === true,
    skipCharacterKnowledgeCognition: armConfig.skip_character_knowledge_cognition !== false,
    lh0ConsumptionEnforcer: armConfig.consumption_lifecycle_enforcer === true,
    lh0Arm: armConfig.arm,
  };
}
