#!/usr/bin/env node
import {
  LIVE_CHARACTER_PROMPT,
  LIVE_DIRECTOR_PROMPT,
} from '../src/lib/live-inference-prompts.mjs';

process.stdout.write(
  JSON.stringify({
    director: LIVE_DIRECTOR_PROMPT,
    character: LIVE_CHARACTER_PROMPT,
  }),
);
