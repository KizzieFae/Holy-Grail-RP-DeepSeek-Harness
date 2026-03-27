# RP Character Migration Guide

This guide standardizes how to convert Janitor-style character assets into the RP app's
AutoGen character format.

Use this guide whenever you migrate any character that starts as a set of files such as:

- `personality`
- `scenario`
- `initial_message`
- `example_dialogue`
- extra notes, lore, or formatting instructions

## Why this guide exists

The RP app does not load Janitor cards directly.

It expects two authored character asset types and may also use an optional scene asset:

- a persistent character card in `data/autogen_characters/<character>.json`
- an optional scene opener in `data/autogen_characters/<character>_initial_message.json`
- an optional scene template in `data/scene_templates/<template>.json` for reusable
  multi-character setup

These assets serve different purposes and should not be merged together.

Character cards define who a character is across scenes.

Openers define a specific legacy scene start.

Scene templates define reusable multi-character setup, role slots, and template-level opening text.

## Runtime expectations

The current RP app behavior is defined by:

- `character_loader.py`
- `scene_opener.py`
- `app.py`

The runtime does not substitute Janitor placeholders in authored character cards or opener files.

Authored opener text is posted as written.

Any section that depends on `{{user}}`, `{{char}}`, or similar placeholders must be rewritten during
conversion so the final text stands on its own without runtime substitution.

### Main character card

The character loader expects a JSON object with fields like:

- `name`
- `description`
- `personality`
- `speaking_style`
- `goals`
- `medium_term_goal`
- `core_goals`
- `voice_profile`
- `reaction_profile`
- `speech_fingerprint`
- `system_prompt`
- `lore_facts`

The main character card is for persistent identity and behavior.

### Initial message file

The opener loader expects a separate file named exactly:

- `<character>_initial_message.json`

That file should contain:

- `label`
- `text`
- `tags`
- `location`
- `time`

The initial message file is for scene-opening text only.

### Scene template file

The scene template loader expects JSON files in:

- `data/scene_templates/*.json`

Scene templates are optional, but they are now the correct place for reusable multi-character scene
setup that should not live inside any one character card.

Template filenames and `template_id` values should start with the original Janitor character's
name so the original source focus remains easy to recognize.

Example:

- `ayame_household_entry_evaluation.json`
- `template_id`: `ayame_household_entry_evaluation`

A template contains:

- `template_id`
- `premise`
- `opening_text`
- `role_slots`

Each role slot currently contains only:

- `role_name`
- `required`
- `presence_constraint`
- optional informational `authority`

Valid `presence_constraint` values are:

- `must_remain`
- `flexible`

### Role assignments happen at scene start

Role assignments are not authored inside the character card or opener file.

They are chosen explicitly in the sidebar when the user starts a scene with a selected template.

When a template is selected, the template still controls role structure and validation, but the user
can choose whether the opening comes from the template's `opening_text`, a character opener, or
custom text.

Current runtime behavior is deterministic:

- every selected character must have a role assignment
- assigned roles must exist in the chosen template
- every required role must be filled before scene start
- `must_remain` characters are kept structurally present in prompts and scene state
- direct exit or absence contradictions for `must_remain` characters are rejected during validation

Template selection controls roles and validation, but the opening source can still be template text,
a character opener, or custom text.

## File naming rules

### Required main card name

- `stacy.json`
- `celina.json`
- `ayame.json`

### Required opener name

- `stacy_initial_message.json`
- `celina_initial_message.json`
- `ayame_initial_message.json`

### Required scene template naming pattern

- `ayame_household_entry_evaluation.json`
- `template_id`: `ayame_household_entry_evaluation`

Always put the original character name first in both the filename and the `template_id`.

This keeps it obvious which Janitor character originally anchored the migrated setup.

### Avoid alternate opener names

Do not rely on names like:

- `stacy_opening.json`
- `stacy_intro.json`
- `stacy_scene_start.json`

The current opener loader looks for `*_initial_message.json`.

## Conversion mapping

### Janitor personality

Use this to build the persistent character card.

Usually map it into:

- `personality`
- `speaking_style`
- `goals`
- `system_prompt`

If the personality text contains durable voice, worldview, or reaction patterns, also derive:

- `core_goals`
- `voice_profile`
- `reaction_profile`
- `speech_fingerprint`

### Janitor scenario

Split this into persistent, situational, and reusable scene-structure parts.

Persistent parts go into:

- `system_prompt`
- `lore_facts`
- sometimes `goals`

Scene-specific setup goes into:

- `<character>_initial_message.json` `text`

Reusable multi-character setup goes into:

- `data/scene_templates/<character>_<template>.json` `premise`
- `data/scene_templates/<character>_<template>.json` `opening_text`
- `data/scene_templates/<character>_<template>.json` `role_slots`

Rule of thumb:

- if it is always true, it belongs in the main card
- if it is only true at the opening of one legacy scene, it belongs in the opener
- if it defines a reusable cast structure like host / guest / guard / observer, it belongs in a scene
  template

If the Janitor scenario repeatedly assumes named positions in a scene such as host, newcomer,
guard, evaluator, attendant, witness, or observer, convert that structure into template role slots
instead of burying those assumptions inside one character's `system_prompt`.

### Janitor initial message

Convert this into the opener file only if it is truly character-specific legacy opener text.

If the opening prose is really about the whole scene setup and should apply whenever a template is
used, move that material into the scene template's `opening_text` instead.

Put the actual opening prose into:

- `text`

Add metadata into:

- `label`
- `tags`
- `location`
- `time`

Do not move the initial message into the main card's `system_prompt`.

Rewrite any placeholder-dependent sections so they no longer rely on `{{user}}`, `{{char}}`, or
similar markers.

If `{{char}}` refers to the authored character, replace it with that character's actual name or
reword the sentence naturally.

If `{{user}}` refers to the player, rewrite it into natural second-person or another phrasing that
reads correctly without substitution.

If the Janitor first message hardcodes a role relationship like "you are the applicant" or "she is
the household guard," decide whether that relationship is:

- a reusable scene-template role setup
- a one-off opener beat
- a stable part of the character's identity

Do not leave temporary scene-role assumptions embedded everywhere by default.

### Janitor example dialogue

Do not paste raw example chats into the opener file.

Do not rely on a non-existent `example_dialogue` schema field unless the app is explicitly extended
to support one.

Instead, distill example dialogue into durable style guidance:

- sentence length
- directness
- politeness vs cruelty
- profanity level
- recurring pet names or insults
- question frequency
- emotional restraint vs expressiveness
- metaphor usage
- dominant rhetorical habits

Map those patterns into:

- `speaking_style`
- `voice_profile`
- `speech_fingerprint`
- `system_prompt`

## Best practices for AutoGen character cards

### Keep the main card persistent

The main card should describe the character as they remain across scenes.

Good fits for the main card:

- identity
- worldview
- long-term motivations
- stable relationship posture
- stable speech patterns
- durable lore facts
- recurring behavioral habits

Bad fits for the main card:

- a single scene's opening beat
- a one-time outfit unless it matters across many scenes
- temporary emotions that only belong to one opener
- one-off narration that should only happen at scene start

### Use `system_prompt` for durable operating instructions

`system_prompt` should hold the character's lasting behavior model.

Good content for `system_prompt`:

- persistent worldview
- durable role-related tendencies that remain true across many scenes
- stable power dynamics
- evergreen setting assumptions
- durable conflict style
- consistent intimacy, trust, or aggression patterns

Avoid using `system_prompt` as:

- a first message
- a transcript
- a scene opener
- a dumping ground for every source file with no structure

If a behavior constraint only applies when a character is assigned a particular scene role in a
particular setup, prefer the scene template and role assignment system over baking that constraint
into the character card.

### Separate fields instead of overloading one field

Do not cram all source material into `system_prompt` alone.

Prefer to split information across:

- `personality`
- `speaking_style`
- `goals`
- `core_goals`
- `voice_profile`
- `reaction_profile`
- `speech_fingerprint`
- `lore_facts`
- `system_prompt`

This makes the card easier to maintain and improves identity consistency.

### Make identity anchors stable

The app carries these fields forward as identity anchors:

- `core_goals`
- `voice_profile`
- `reaction_profile`
- `speech_fingerprint`

Treat them as compact, durable truth.

Do not put temporary scene-specific details in them.

### Write for self-only responses

Character agents are expected to produce self-only moves.

The character card should reinforce that the character:

- speaks only for themselves
- acts only for themselves
- does not narrate the user's actions
- does not narrate other characters' inner states

### Prefer natural language over placeholders

Do not rely on Janitor placeholders in any autogen asset.

Rewrite any placeholder-dependent sentence during conversion so the final text works correctly on
its own.

Do not assume the runtime will substitute, rename, or reinterpret placeholder-based text for you.

Avoid:

- `{{user}}`
- `{{char}}`
- `{{user_name}}`

Prefer:

- `you`
- the authored character's actual name when replacing `{{char}}`
- `the other person`
- `your subject`
- `the player`
- a more specific natural phrase when needed

If possible, rewrite the line so no special placeholder is needed at all.

### Avoid contradiction between fields

Before finalizing a card, check that:

- `personality` matches `system_prompt`
- `speaking_style` matches `voice_profile` and `speech_fingerprint`
- `goals` align with `core_goals`
- `lore_facts` do not conflict with the prompt

### Keep prose dense, not bloated

Longer prompts are not automatically better.

Prefer:

- concrete behavior
- specific voice cues
- explicit worldview
- durable motivations

Avoid:

- repeated wording
- multiple paragraphs that say the same thing
- scene narration disguised as character guidance

## Best practices for initial messages

### Treat the opener as a scene asset, not a character asset

The opener should answer:

- where are we
- what just happened
- what is the emotional temperature
- what is the immediate pressure
- what is the opening interaction

It should not redefine the whole character.

### Keep the opener grounded in the current scene

Good opener content:

- immediate body language
- immediate situation
- first conflict beat
- first sensory details
- first question or hook

Bad opener content:

- full personality essay
- all backstory
- repeated character instructions already in the main card
- generic information that belongs in `system_prompt`

### End with a clean interaction hook when appropriate

If the opener is user-facing prose, it can end with a prompt like:

- `What do you say or do?`

This is often a good pattern for scene start assets.

### Keep metadata useful

Use opener metadata consistently:

- `label` should be human-readable in the UI
- `tags` should help identify the opener's tone or setup
- `location` should name the starting place
- `time` should mark the opening moment clearly

### Use second-person when the opener addresses the player directly

For openers derived from Janitor first messages, second-person wording is usually safest:

- `you`
- `your`
- `What do you say or do?`

This avoids unsupported placeholder substitution.

If you are using a scene template, remember that the template's `opening_text` is now the better
home for opening prose that belongs to the whole setup rather than to a single character asset.

## Best practices for scene templates and role-aware migration

### Create a scene template when the setup is reusable and multi-character

Good candidates for a scene template:

- entry interviews
- household evaluations
- guarded meetings
- ritual gatherings
- negotiations with stable positions in the room
- scenes where one or more roles must remain present throughout

If the source material keeps implying the same cast structure across variants, create a template.

### Put role slots in the template, not in the file name or card schema

The current V1 template system models roles as flat slots.

Use role slots for things like:

- `host`
- `applicant`
- `guard`
- `observer`

Do not create separate duplicate character cards just to represent the same character in different
scene roles.

### Keep explicit role assignment out of authored character assets

Current assignments are chosen per scene at runtime.

That means a migrated character card should not assume it is always the `host`, always the
`applicant`, or always the `guard` unless that is actually part of the character's stable identity.

### Use `must_remain` only for structural presence requirements

`must_remain` is enforced deterministically.

Use it for roles that must stay present in the scene framing.

Do not treat it as a soft flavor hint.

### Treat `authority` as informational only

The current V1 system records `authority`, but it does not enforce authority-based reasoning.

Do not write migration guidance as if `authority` automatically changes behavior at runtime.

### Separate three kinds of text cleanly

When converting Janitor assets, separate:

- stable identity text for the character card
- scene-opening prose for a legacy opener or template `opening_text`
- reusable cast structure for the scene template

## Recommended migration workflow

### Step 1: collect source assets

Gather all source text for the character:

- personality
- scenario
- initial message
- example dialogue
- lore notes
- author notes

### Step 2: separate persistent from situational material

Create three buckets:

- persistent character identity
- opening-scene material
- reusable scene-template material

Reusable scene-template material includes:

- recurring role positions in the scene
- premise text that describes the setup rather than one specific character
- opening prose that should fire whenever that setup is selected
- presence rules like who must remain in the scene

### Step 3: build the main character card

Create `<character>.json` first.

Focus on:

- who the character is
- how they speak
- what they want
- how they interpret events
- what stable facts define them

### Step 4: decide whether a scene template is needed

Create a scene template when the source material defines a reusable multi-character setup.

Name the file and `template_id` with the original character first, using a pattern like
`<character>_<scene_template>`.

Focus on:

- the template premise
- the template opening text
- the list of role slots
- which roles are required
- which roles are `must_remain` versus `flexible`
- optional informational `authority` labels

### Step 5: build the opener file if you still need one

Create `<character>_initial_message.json`.

Use the original initial message as the base.

Skip this file if the opening prose has been moved into a reusable scene template's `opening_text`
and you do not need a separate legacy opener for the character.

Rewrite any placeholder-dependent sections so they no longer rely on `{{user}}`, `{{char}}`, or
similar markers.

If `{{char}}` refers to the authored character, replace it with that character's actual name or
reword the sentence naturally.

If `{{user}}` refers to the player, rewrite it into natural second-person or another phrasing that
reads correctly without substitution.

### Step 6: distill example dialogue

Convert example dialogue into style rules rather than raw transcript blocks.

### Step 7: validate file naming and schema

Check that:

- the main card file name matches the character
- any opener ends in `_initial_message.json`
- any scene template lives in `data/scene_templates/`, uses a matching `template_id`, and starts
  with the original character name
- the opener uses `label` and `text`, not `system_prompt`
- the main card contains `system_prompt`
- any template uses only supported V1 role-slot fields

### Step 8: verify against the app's expectations

Before considering the migration done, verify:

- the character loads through `CharacterLoader`
- any opener loads through `OpenerManager`
- any scene template loads through `SceneTemplateManager`
- selected template scenes require explicit role assignment for each selected character
- no unsupported placeholders remain
- every placeholder-dependent section has been rewritten to stand on its own
- example dialogue has been distilled into style guidance
- stable identity, opening prose, and reusable template structure are clearly separated
- file naming matches the loader's expectations

## Quick decision rules

### If the text describes who the character always is

Put it in the main character card.

### If the text describes what is happening right now at scene start

Put it in the opener file.

### If the text describes a reusable multi-character setup with named positions

Put it in a scene template.

### If the text demonstrates voice rather than story state

Distill it into style fields.

### If the text looks like a literal first post

Put it in `*_initial_message.json` unless it should instead be the reusable template `opening_text`.

## Common migration mistakes

- putting the initial message into `system_prompt`
- naming the opener something other than `*_initial_message.json`
- forcing reusable scene structure into one character card instead of a scene template
- hardcoding scene-role assumptions into every migrated asset when they should be explicit runtime
  assignments
- keeping `{{user}}` or `{{char}}` placeholders in autogen files
- assuming runtime will substitute or rename placeholder-based text in authored assets
- stuffing example dialogue into the wrong file without distillation
- mixing one-scene setup into stable identity anchors
- putting `must_remain` obligations into prose alone instead of the template slot definition
- repeating the same instructions in multiple fields
- writing opener files as if they were main character cards

## Minimal templates

### Main character card template

```json
{
  "name": "Character Name",
  "description": "Short selector description",
  "personality": "Persistent personality summary",
  "speaking_style": "How the character talks",
  "goals": "Main ongoing motivations",
  "medium_term_goal": "Current medium-term objective",
  "core_goals": [
    "Stable goal one",
    "Stable goal two"
  ],
  "voice_profile": {
    "speech_style": "brief",
    "sentence_length": "short",
    "formality": "low"
  },
  "reaction_profile": {
    "worldview": "suspicious",
    "trust_bias": "low",
    "conflict_style": "confrontational"
  },
  "speech_fingerprint": {
    "avg_sentence_length": "short",
    "question_frequency": "high",
    "formality_level": "casual"
  },
  "system_prompt": "Durable persona instructions",
  "lore_facts": [
    "Stable fact one",
    "Stable fact two"
  ]
}
```

### Initial message template

```json
{
  "label": "Character Default",
  "text": "Opening scene prose goes here.",
  "tags": ["tone", "setup"],
  "location": "Starting location",
  "time": "Starting time"
}
```

### Scene template template

```json
{
  "template_id": "ayame_household_entry_evaluation",
  "premise": "A newcomer is evaluated while the host and guard remain present.",
  "opening_text": "The household receives a newcomer inside a controlled interior space.",
  "role_slots": [
    {
      "role_name": "host",
      "required": true,
      "presence_constraint": "must_remain",
      "authority": "high"
    },
    {
      "role_name": "applicant",
      "required": true,
      "presence_constraint": "must_remain",
      "authority": "low"
    },
    {
      "role_name": "observer",
      "required": false,
      "presence_constraint": "flexible",
      "authority": "low"
    }
  ]
}
```

## Migration completion checklist

- the main card exists as `<character>.json`
- any needed opener exists as `<character>_initial_message.json`
- any needed scene template exists in `data/scene_templates/<character>_<template>.json`
- any needed scene template filename starts with the original character name
- any needed scene template `template_id` starts with the original character name
- the main card contains the character `system_prompt`
- any opener contains `text`, not `system_prompt`
- any template uses supported V1 fields only
- no Janitor placeholders remain
- every placeholder-dependent section has been rewritten to stand on its own
- example dialogue has been distilled into style guidance
- stable identity, opening prose, and reusable template structure are clearly separated
- explicit runtime role assignment is assumed where templates are used
- file naming matches the loader's expectations

## Related files

- `character_loader.py`
- `scene_opener.py`
- `scene_template.py`
- `../data/scene_templates/`
- `README.md`
- `../data/autogen_characters/`
