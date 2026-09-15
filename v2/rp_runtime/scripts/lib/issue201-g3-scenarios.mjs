/** Frozen G3 scenario definitions (Package D parity). */

export const G3_SCENARIOS = {
  ayame_controlled: {
    id: 'ayame_household_entry_evaluation',
    scenario_key: 'ayame_controlled',
    characters: ['ayame', 'kizzie'],
    roleAssignments: { ayame: 'host', kizzie: 'applicant' },
    playerCharacterFileId: 'kizzie',
    userName: 'Kizzie',
    openerPreference: null,
    playerPost:
      'Kizzie glanced up, double-checking the house number and then steeled herself before knocking.',
  },
  ayame_archive_interview: {
    id: 'ayame_archive_interview',
    scenario_key: 'ayame_archive_interview',
    characters: ['ayame', 'kizzie'],
    roleAssignments: { ayame: 'host', kizzie: 'applicant' },
    playerCharacterFileId: 'kizzie',
    userName: 'Kizzie',
    openerPreference: null,
    playerPost:
      'Kizzie steadied herself at the archive consultation table. '
      + '"Could you explain the household policies that would apply to my tenancy interview?"',
    g3e: true,
  },
  arkham_stress: {
    id: 'arkham_asylum_mess_hall_arena',
    scenario_key: 'arkham_stress',
    characters: ['harley_quinn', 'poison_ivy', 'magpie'],
    roleAssignments: {
      harley_quinn: 'instigator',
      poison_ivy: 'instigator_accomplice',
      magpie: 'new_arrival',
    },
    playerCharacterFileId: 'magpie',
    userName: 'Magpie',
    openerPreference: 'mess_hall_magpie',
    playerPost:
      'Magpie keeps her eyes on the guard\'s gold watch while she pushes food around her tray. '
      + 'When Harley\'s voice carries across the table, she murmurs just loud enough to be heard: '
      + '"Pretty things never stay pretty in here for long."',
  },
};
